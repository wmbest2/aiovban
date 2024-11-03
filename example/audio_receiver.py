import asyncio
from dataclasses import dataclass, field
from enum import Enum

import pyaudio

from asyncvban.asyncio import AsyncVBANClient
from asyncvban.asyncio.streams import VBANIncomingStream
from asyncvban.enums import VBANSampleRate
from asyncvban.packet import VBANPacket
from asyncvban.packet.headers.audio import VBANAudioHeader, BitResolution


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
    framebuffer_size: int = 100

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
        )

    def check_pyaudio(self, packet: VBANPacket):
        header: VBANAudioHeader = packet.header
        if header.sample_rate != self.sample_rate or header.channels != self.channels or header.bit_resolution != self.format:
            old_stream = self._stream
            self.channels = header.channels
            self.sample_rate = header.sample_rate
            self.format = header.bit_resolution
            print(f"Changing stream to {header.channels} channels, {header.sample_rate.rate} Hz, {header.samples_per_frame} samples per frame for stream {header.streamname}")
            old_stream.stop_stream()
            self._stream = self.setup_stream()
            old_stream.close()

    async def handle_packets(self, packets: [VBANPacket]):
        if packets:
            self.check_pyaudio(packets[0])
        [self._stream.write(packet.body) for packet in packets]


    async def listen(self):
        self._stream.start_stream()
        async def wait_for_packet():
            packet = await self.stream.get_packet()
            return packet if type(packet.header) == VBANAudioHeader else None

        async def gather_frames(frame_count):
            return await asyncio.gather(
                *[wait_for_packet() for _ in range(frame_count)]
            )

        while True:
            packets = await gather_frames(self.framebuffer_size)
            await self.handle_packets(packets)

    def stop(self):
        self._stream.stop_stream()
        self._stream.close()
        self._pyaudio.terminate()


async def run_loop():
    client = AsyncVBANClient(ignore_audio_streams=False)
    asyncio.create_task(client.listen('0.0.0.0', 6980)) # Listen for all incoming packets

    windows_host = client.register_device('bill.local', 6980)
    windows_mic_out = windows_host.receive_stream('Windows Mic Out')

    command_stream = await windows_host.command_stream(30, 'Command1')
    await command_stream.send_text('Strip[0].Gain = 0.5;')
    await asyncio.sleep(1)
    await command_stream.send_text('Command.Restart = 1;')

    receiver = VBANAudioPlayer(sample_rate=VBANSampleRate.RATE_44100, channels=2, stream=windows_mic_out)

    await receiver.listen()

asyncio.run(run_loop())