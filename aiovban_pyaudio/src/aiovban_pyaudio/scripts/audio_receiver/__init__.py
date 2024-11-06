import asyncio
import sys

import pyaudio
from setproctitle import setproctitle

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient
from aiovban.asyncio.util import BackPressureStrategy
from aiovban.enums import Features
from ..util import get_device_by_name
from ... import VBANAudioPlayer, VBANAudioSender


def setup_logging():
    import logging

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    print("Setting up logging at level INFO")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


async def run_loop():
    application_data = VBANApplicationData(
        application_name="VBAN Audio Receiver",
        features=Features.Audio | Features.Text,
        device_type=DeviceType.Receptor,
        version="0.2.1",
    )
    client = AsyncVBANClient(
        ignore_audio_streams=False, application_data=application_data
    )
    asyncio.create_task(
        client.listen("0.0.0.0", 6980)
    )  # Listen for all incoming packets

    windows_host = client.register_device("bill.local", 6980)
    windows_mic_out = windows_host.receive_stream("Windows Mic Out")
    mac_in = await windows_host.send_stream("Mac In")
    pyaudio_instance = pyaudio.PyAudio()

    for i in range(pyaudio_instance.get_device_count()):
        print(pyaudio_instance.get_device_info_by_index(i))

    command_stream = await windows_host.text_stream("Command1")
    rt_stream = await windows_host.rt_stream(
        30, back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST
    )
    await command_stream.send_text("Strip[0].Gain = 0.5;")
    await asyncio.sleep(1)
    await command_stream.send_text("Command.Restart = 1;")
    print(await rt_stream.get_packet())
    print((await rt_stream.get_packet()).body)


    receiver_device = get_device_by_name(pyaudio_instance, "Windows Audio In")
    sender_device = get_device_by_name(pyaudio_instance, "Air Pods")

    receiver = VBANAudioPlayer(
        stream=windows_mic_out, pyaudio=pyaudio_instance, device_index=receiver_device
    )
    sender = VBANAudioSender(
        stream=mac_in, pyaudio=pyaudio_instance, device_index=sender_device
    )

    await asyncio.gather(receiver.listen(), sender.listen())


def main():
    setproctitle("VBAN Audio Receiver")
    setup_logging()
    asyncio.run(run_loop())
