import asyncio
import sys

from setproctitle import setproctitle

from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import BackPressureStrategy
from ... import VBANAudioPlayer


def setup_logging():
    import logging
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    print('Setting up logging at level INFO')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


async def run_loop():
    client = AsyncVBANClient(ignore_audio_streams=False)
    asyncio.create_task(client.listen('0.0.0.0', 6980)) # Listen for all incoming packets

    windows_host = client.register_device('bill.local', 6980)
    windows_mic_out = windows_host.receive_stream('Windows Mic Out')


    command_stream = await windows_host.text_stream('Command1')
    rt_stream = await windows_host.rt_stream(30, back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST)
    await command_stream.send_text('Strip[0].Gain = 0.5;')
    await asyncio.sleep(1)
    await command_stream.send_text('Command.Restart = 1;')
    print(await rt_stream.get_packet())
    print((await rt_stream.get_packet()).body)


    receiver = VBANAudioPlayer(stream=windows_mic_out)

    await receiver.listen()


def main():
    setproctitle('VBAN Audio Receiver')
    setup_logging()
    asyncio.run(run_loop())
