import asyncio
import sys

import pyaudio
from setproctitle import setproctitle

from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import VBANSampleRate, BackPressureStrategy
from aiovban.packet.body.service import RTPacketBodyType0
from aiovban_pyaudio import VBANAudioPlayer


def setup_logging():
    import logging
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


async def run_loop():
    client = AsyncVBANClient(ignore_audio_streams=False)
    asyncio.create_task(client.listen('0.0.0.0', 6980)) # Listen for all incoming packets

    windows_host = client.register_device('bill.local', 6980)
    windows_mic_out = windows_host.receive_stream('Windows Mic Out')

    command_stream = await windows_host.command_stream(30, 'Command1', back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST)
    await command_stream.send_text('Strip[0].Gain = 0.5;')
    await asyncio.sleep(1)
    await command_stream.send_text('Command.Restart = 1;')
    print(await command_stream.get_packet())
    print(RTPacketBodyType0.unpack((await command_stream.get_packet()).body))


    receiver = VBANAudioPlayer(sample_rate=VBANSampleRate.RATE_44100, channels=2, stream=windows_mic_out)

    await receiver.listen()


for i in range(pyaudio.PyAudio().get_device_count()):
    print(pyaudio.PyAudio().get_device_info_by_index(i))

setproctitle('VBAN Audio Receiver')
setup_logging()
asyncio.run(run_loop())
