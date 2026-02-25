import asyncio
import logging
from dataclasses import field, dataclass
from typing import Any

import pyaudio

from aiovban import VBANSampleRate
from aiovban.asyncio.streams import VBANIncomingStream
from aiovban.packet import VBANPacket, VBANHeader
from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution
from .enums import VBANPyAudioFormatMapping
from .scripts.util import ProbabilityFilter
from .util import FrameBuffer

logger = logging.getLogger(__name__)
probability_filter = ProbabilityFilter()
probability_filter.probability = 0.001
probability_logger = logging.getLogger(__name__)
probability_logger.addFilter(probability_filter)


@dataclass
class VBANAudioPlayer:
    stream: VBANIncomingStream  # This stream should be accessed from the original loop, not the background thread

    device_index: int = 0
    sample_rate: VBANSampleRate = VBANSampleRate.RATE_48000
    channels: int = 2
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 512
    max_framebuffer_size: int = 8192

    pyaudio: Any = None
    _stream: Any = field(
        init=False
    )  # The audio stream should be accessed from the background thread
    _framebuffer: FrameBuffer = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._synced = False
        self._framebuffer = FrameBuffer(
            self.max_framebuffer_size, self.format.byte_width * self.channels
        )

        if not self.pyaudio:
            self.pyaudio = pyaudio.PyAudio()

    def setup_stream(self):
        return self.pyaudio.open(
            format=VBANPyAudioFormatMapping(self.format).pyaudio_format,
            channels=self.channels,
            rate=self.sample_rate.rate,
            output=True,
            frames_per_buffer=self.framebuffer_size,
            output_device_index=self.device_index,
            stream_callback=self.data_callback_in_thread,
        )

    async def check_pyaudio(self, packet: VBANPacket):
        header = packet.header
        if not isinstance(header, VBANAudioHeader):
            return False

        if (
            header.sample_rate != self.sample_rate
            or header.channels != self.channels
            or header.bit_resolution != self.format
        ):
            print(
                f"Changing stream to {header.channels} channels, {header.sample_rate.rate} Hz, {header.samples_per_frame} samples per frame for stream {header.streamname}"
            )
            logger.info("Stopping stream")
            self._stream.stop_stream()
            logger.info("Closing stream")
            self._stream.close()

            self.channels = header.channels
            self.sample_rate = header.sample_rate
            self.format = header.bit_resolution

            logger.info("Opening new stream")
            self._stream = self.setup_stream()
            logger.info("Starting new stream")
            self._stream.start_stream()

            return True
        return False

    def silence(self, num_frames=0):
        if self.format == BitResolution.BYTE8:
            return b"\x80" * num_frames * self.channels
        return b"\x00" * num_frames * self.format.byte_width * self.channels

    def data_callback_in_thread(self, in_data, frame_count, time_info, status):
        (buffer_size, available_frame_count) = self._framebuffer.size()

        # Wait for a cushion of data before starting to avoid immediate underflow
        if not self._synced:
            if available_frame_count < frame_count * 2:  # Wait for 2 buffers worth
                return self.silence(num_frames=frame_count), pyaudio.paContinue
            logger.debug(
                f"Cushion reached ({available_frame_count} frames), starting playback"
            )
            self._synced = True

        (buffer_data, available_frames) = self.commit_data(frame_count)
        if available_frames < frame_count:
            # Only log underflow occasionally to avoid flooding
            if probability_filter.filter(None):
                logger.warning(
                    f"Buffer underflow: {frame_count - available_frames} frames with latency of {self._estimated_latency(frame_count - available_frames):.2f} ms"
                )
            return (
                self.silence(num_frames=frame_count - available_frames) + buffer_data,
                pyaudio.paContinue,
            )
        return buffer_data, pyaudio.paContinue

    def _frames_to_byte_count(self, frames):
        return frames * self.channels * self.format.byte_width

    def _estimated_latency(self, frame_count):
        return (frame_count / self.sample_rate.rate) * 1000  # ms

    def commit_data(self, frame_count):
        (buffer_size, available) = self._framebuffer.size()
        probability_logger.info(
            f"Buffer size: {buffer_size} \n Current Latency: {self._estimated_latency(available)} ms"
        )

        (buffer_data, available_frames, dropped_frames) = self._framebuffer.read(
            frame_count
        )
        if dropped_frames > 0:
            logger.info(
                f"Dropping {dropped_frames} frames out of {frame_count} frames with maximum of {self.max_framebuffer_size} frames"
            )
        return buffer_data, available_frames

    def write_data(self, packet: VBANPacket):
        header: VBANAudioHeader = packet.header
        byte_count = (
            header.samples_per_frame * header.channels * header.bit_resolution.byte_width
        )
        data = packet.body.pack()[:byte_count]
        self._framebuffer.write(data, header.samples_per_frame)

    def sync_buffers(self):
        self._framebuffer.synchronize(self.format.byte_width * self.channels)

    async def listen(self):
        self._stream: pyaudio.Stream = self.setup_stream()
        self._stream.start_stream()

        try:
            while True:
                packet = await self.stream.get_packet()
                resync = await self.check_pyaudio(packet)
                if resync:
                    self.sync_buffers()

                self.write_data(packet)
        except asyncio.CancelledError as _:
            self.stop()

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
