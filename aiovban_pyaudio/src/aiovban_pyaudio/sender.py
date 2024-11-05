import asyncio
import logging
from dataclasses import field, dataclass
from typing import Any

import pyaudio

from aiovban import VBANSampleRate
from aiovban.asyncio.streams import VBANOutgoingStream
from aiovban.packet import VBANPacket, BytesBody
from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution, Codec
from .enums import VBANPyAudioFormatMapping

logger = logging.getLogger(__package__)


@dataclass
class VBANAudioSender:
    stream: VBANOutgoingStream
    device_index: int = 0

    sample_rate: VBANSampleRate = VBANSampleRate.RATE_48000
    channels: int = 2
    format: BitResolution = BitResolution.INT16
    framebuffer_size: int = 128
    sample_buffer_size: int = 1

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
            frames_per_buffer=self.framebuffer_size * self.sample_buffer_size,
            stream_callback=self.audio_callback
        )

    def split_bytes_into_chunks(self, data, chunk_size):
        """Splits bytes into chunks of a given size."""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    async def pack_audio_data(self, audio_data, frame_count):
        packet = VBANPacket(
            header=VBANAudioHeader(
                streamname=self.stream.name,
                sample_rate=self.sample_rate,
                codec=Codec.PCM,
                channels=self.channels,
                bit_resolution=self.format,
                samples_per_frame=self.framebuffer_size,
            ),
            body=BytesBody(audio_data)
        )
        await self.stream.send_packet(packet)

    async def send_all_audio_data(self, audio_data, frame_count):
        chunks = self.split_bytes_into_chunks(audio_data, len(audio_data) // self.sample_buffer_size)
        for chunk in chunks:
            await self.pack_audio_data(chunk, frame_count)

    def audio_callback(self, in_data: bytes, frame_count, time_info, status):
        if self._loop:
            self._loop.create_task(self.send_all_audio_data(in_data, frame_count))

        return None, pyaudio.paContinue


    async def listen(self):
        self._loop = asyncio.get_running_loop()
        self._stream.start_stream()
        stream_waiter = asyncio.Future()
        await stream_waiter

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
