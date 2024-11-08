import asyncio
import logging
import threading
from asyncio import AbstractEventLoop
from dataclasses import field, dataclass
from typing import Any

import pyaudio

from aiovban import VBANSampleRate
from aiovban.asyncio.streams import VBANOutgoingStream
from aiovban.packet import VBANPacket, BytesBody
from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution, Codec
from .enums import VBANPyAudioFormatMapping
from .util import run_on_background_thread

logger = logging.getLogger(__package__)


@dataclass
class VBANAudioSender:
    stream: VBANOutgoingStream
    device_index: int = 0

    sample_rate: VBANSampleRate = VBANSampleRate.RATE_48000
    channels: int = 2
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 128
    sample_buffer_size: int = 3

    pyaudio: Any = field(default_factory=pyaudio.PyAudio, repr=False)
    _stream: Any = field(init=False, repr=False)
    _loop: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._stream = self.setup_stream()

    def setup_stream(self):
        return self.pyaudio.open(
            format=VBANPyAudioFormatMapping(self.format).pyaudio_format,
            channels=self.channels,
            rate=self.sample_rate.rate,
            input=True,
            input_device_index=self.device_index,
        )

    def split_bytes_into_chunks(self, data, chunk_size):
        """Splits bytes into chunks of a given size."""
        return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    async def pack_audio_data(self, audio_data):
        packet = VBANPacket(
            header=VBANAudioHeader(
                streamname=self.stream.name,
                sample_rate=self.sample_rate,
                codec=Codec.PCM,
                channels=self.channels,
                bit_resolution=self.format,
                samples_per_frame=self.framebuffer_size,
            ),
            body=BytesBody(audio_data),
        )
        if self._loop:
            asyncio.create_task(self.stream.send_packet(packet))

    async def send_all_audio_data(self, audio_data):
        chunks = self.split_bytes_into_chunks(
            audio_data, len(audio_data) // self.sample_buffer_size
        )
        for chunk in chunks:
            await self.pack_audio_data(chunk)

    def read_stream(self, amount):
        return self._stream.read(amount, exception_on_overflow=False)

    @run_on_background_thread
    async def listen(self, origin_loop: AbstractEventLoop):
        self._loop = origin_loop
        self._stream.start_stream()

        try:
            while True:
                audio_data = self.read_stream(
                    self.framebuffer_size * self.sample_buffer_size
                )
                asyncio.run_coroutine_threadsafe(
                    self.send_all_audio_data(audio_data), origin_loop
                ).result()
        except asyncio.CancelledError as _:
            self.stop()

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
