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
probability_filter.probability = 0.01
probability_logger = logging.getLogger(__name__)
probability_logger.addFilter(probability_filter)


@dataclass
class VBANAudioPlayer:
    stream: VBANIncomingStream # This stream should be accessed from the original loop, not the background thread

    device_index: int = 0
    sample_rate: VBANSampleRate = VBANSampleRate.RATE_48000
    channels: int = 2
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 512
    max_framebuffer_size: int = framebuffer_size * 4

    pyaudio: Any = None
    _stream: Any = field(init=False) # The audio stream should be accessed from the background thread
    _framebuffer: FrameBuffer = field(default=None, init=False, repr=False)
    _loop: Any = field(default=None, init=False)

    def __post_init__(self):
        self._synced = False
        self._framebuffer = FrameBuffer(self.max_framebuffer_size, self.format.byte_width * self.channels)
        self._loop = asyncio.get_event_loop()

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
            stream_callback=self.data_callback_in_thread
        )

    async def check_pyaudio(self, packet: VBANPacket):
        header: VBANHeader = packet.header
        if (
                isinstance(header, VBANAudioHeader)
                and header.sample_rate != self.sample_rate
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
        return b"\x00" * num_frames * self.format.byte_width * self.channels

    def data_callback_in_thread(self, in_data, frame_count, time_info, status):
        if self._loop and self._loop.is_running():

            # Synchronize the buffers, since we started reading off the network before starting this stream
            if not self._synced:
                logger.debug("Synchronizing buffers")
                asyncio.run_coroutine_threadsafe(self.sync_buffers(), self._loop).result()
                self._synced = True
                return self.silence(num_frames=frame_count), pyaudio.paContinue

            (buffer_data, available_frame_count) = asyncio.run_coroutine_threadsafe(self.commit_data(frame_count), self._loop).result()
            if available_frame_count < frame_count:
                print(f"Buffer underflow: {frame_count - available_frame_count} frames with latency of {self._estimated_latency(frame_count)} ms")
                return self.silence(frame_count - available_frame_count) + buffer_data, pyaudio.paContinue
            return buffer_data, pyaudio.paContinue

        return self.silence(frame_count), pyaudio.paContinue

    def _frames_to_byte_count(self, frames):
        return frames * self.channels * self.format.byte_width

    def _estimated_latency(self, frame_count):
        return (frame_count / self.sample_rate.rate) * 1000 # ms

    async def commit_data(self, frame_count):
        (buffer_size, available) = await self._framebuffer.size()
        probability_logger.info(f"Buffer size: {buffer_size} \n Current Latency: {self._estimated_latency(available)} ms")

        (buffer_data, available_frames, dropped_frames) = await self._framebuffer.read(frame_count)
        if dropped_frames > 0:
            logger.info(
                f"Dropping {dropped_frames} frames out of {frame_count} frames with maximum of {self.max_framebuffer_size} frames")
        return buffer_data, available_frames

    async def write_data(self, packet: VBANPacket):
        data = packet.body.pack()
        header: VBANAudioHeader = packet.header
        await self._framebuffer.write(data, header.samples_per_frame)

    async def sync_buffers(self):
        await self._framebuffer.synchronize(self.format.byte_width * self.channels)

    async def listen(self):
        self._stream: pyaudio.Stream = self.setup_stream()
        self._stream.start_stream()
        self._stream.is_active()

        try:
            while True:
                packet = await self.stream.get_packet()
                resync = await self.check_pyaudio(packet)
                if resync:
                    await self.sync_buffers()

                await self.write_data(packet)
        except asyncio.CancelledError as _:
            self.stop()

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
