import asyncio
import functools
import threading
from dataclasses import field, dataclass
from typing import Any

import pyaudio

from aiovban import VBANSampleRate
from aiovban.asyncio.streams import VBANIncomingStream
from aiovban.packet import VBANPacket, VBANHeader
from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution
from .enums import VBANPyAudioFormatMapping
from .util import run_on_background_thread


@dataclass
class VBANAudioPlayer:
    stream: VBANIncomingStream

    device_index: int = 0
    sample_rate: VBANSampleRate = VBANSampleRate.RATE_48000
    channels: int = 1
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 100

    pyaudio: Any = None
    _stream: Any = field(init=False)

    def __post_init__(self):
        self._stream = self.setup_stream()
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
        )

    def check_pyaudio(self, packet: VBANPacket):
        header: VBANHeader = packet.header
        if (
            isinstance(header, VBANAudioHeader)
            and header.sample_rate != self.sample_rate
            or header.channels != self.channels
            or header.bit_resolution != self.format
        ):
            old_stream = self._stream
            self.channels = header.channels
            self.sample_rate = header.sample_rate
            self.format = header.bit_resolution
            print(
                f"Changing stream to {header.channels} channels, {header.sample_rate.rate} Hz, {header.samples_per_frame} samples per frame for stream {header.streamname}"
            )
            self._stream = self.setup_stream()
            old_stream.stop_stream()
            old_stream.close()

    async def handle_packets(self, packets: [VBANPacket]):
        if packets:
            self.check_pyaudio(packets[0])
            data = functools.reduce(
                lambda a, b: a + b, [bytes(packet.body) for packet in packets]
            )
            self._stream.write(data)

    async def gather_frames(self, frame_count):
        return await asyncio.gather(
            *[self.stream.get_packet() for _ in range(frame_count)]
        )

    @run_on_background_thread
    async def listen(self):
        self._stream.start_stream()

        try:
            while True:
                packets = await self.gather_frames(self.framebuffer_size)
                await self.handle_packets(packets)
        except asyncio.CancelledError as _:
            self.stop()

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
