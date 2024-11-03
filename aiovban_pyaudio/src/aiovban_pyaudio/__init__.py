import asyncio
import functools
from dataclasses import dataclass, field
from enum import Enum

import pyaudio

from aiovban.asyncio.streams import VBANIncomingStream
from aiovban.enums import VBANSampleRate
from aiovban.packet import VBANPacket, VBANHeader

from aiovban.packet.headers.audio import BitResolution, VBANAudioHeader


class VBANPyAudioFormatMapping(Enum):
    INT16 = BitResolution.INT16, pyaudio.paInt16
    INT24 = BitResolution.INT24, pyaudio.paInt24
    INT32 = BitResolution.INT32, pyaudio.paInt32
    FLOAT32 = BitResolution.FLOAT32, pyaudio.paFloat32

    def __new__(cls, data, pyaudio_format):
        obj = object.__new__(cls)
        obj.key = obj._value_ = data
        obj.pyaudio_format = pyaudio_format
        return obj


@dataclass
class VBANAudioPlayer:
    stream: VBANIncomingStream

    sample_rate: VBANSampleRate = VBANSampleRate.RATE_44100
    channels: int = 1
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 200

    _pyaudio: pyaudio.PyAudio = field(default=pyaudio.PyAudio(), init=False)
    _stream: pyaudio.Stream = field(init=False)

    def __post_init__(self):
        self._stream = self.setup_stream()

    def setup_stream(self):
        return self._pyaudio.open(
            format=VBANPyAudioFormatMapping(self.format).pyaudio_format,
            channels=self.channels,
            rate=self.sample_rate.rate,
            output=True,
            frames_per_buffer=self.framebuffer_size
        )

    def check_pyaudio(self, packet: VBANPacket):
        header: VBANHeader = packet.header
        if isinstance(header, VBANAudioHeader) and header.sample_rate != self.sample_rate or header.channels != self.channels or header.bit_resolution != self.format:
            old_stream = self._stream
            self.channels = header.channels
            self.sample_rate = header.sample_rate
            self.format = header.bit_resolution
            print(f"Changing stream to {header.channels} channels, {header.sample_rate.rate} Hz, {header.samples_per_frame} samples per frame for stream {header.streamname}")
            self._stream = self.setup_stream()
            old_stream.stop_stream()
            old_stream.close()

    async def handle_packets(self, packets: [VBANPacket]):
        if packets:
            self.check_pyaudio(packets[0])
            bytes = functools.reduce(lambda a, b: a + b, [packet.body for packet in packets])
            self._stream.write(bytes)


    async def listen(self):
        self._stream.start_stream()

        async def gather_frames(frame_count):
            return await asyncio.gather(
                *[self.stream.get_packet() for _ in range(frame_count)]
            )

        while True:
            packets = await gather_frames(self.framebuffer_size)
            asyncio.create_task(self.handle_packets(packets))

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
        self._pyaudio.terminate()
