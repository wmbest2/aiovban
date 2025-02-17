import argparse
import asyncio
import sys

import pyaudio
from setproctitle import setproctitle

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import Features
from aiovban.asyncio.util import BackPressureStrategy
from ..util import get_device_by_name
from ... import VBANAudioPlayer


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


async def wait_for_first_done(*tasks):
    (done_tasks, pending) = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    for pending in pending:
        pending.cancel()
    return done_tasks


async def run_loop(config):
    application_data = VBANApplicationData(
        application_name="VBAN Audio Receiver",
        features=Features.Audio | Features.Text,
        device_type=DeviceType.Receptor,
        version="0.2.1",
    )
    client = AsyncVBANClient(
        ignore_audio_streams=False, application_data=application_data
    )
    listen_future = await client.listen(config.host_address, config.host_port)

    pyaudio_instance = pyaudio.PyAudio()

    output_device = get_device_by_name(pyaudio_instance, config.output_device)

    players = []
    for stream in config.streams:
        full_address, stream_name = stream.split("/")
        if ":" in full_address:
            address, port = full_address.split(":")
        else:
            address = full_address
            port = 6980

        host = client.register_device(address, port)
        receiver = host.receive_stream(stream_name, back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST)
        players.append(
            VBANAudioPlayer(
                stream=receiver, pyaudio=pyaudio_instance, device_index=output_device
            )
        )

    await wait_for_first_done(listen_future, *map(lambda p: p.listen(), players))


def main():
    parser = argparse.ArgumentParser(
        prog="aioVBAN Stream Receiver",
        description="Receives Audio Streams from VBAN and plays them back",
    )
    parser.add_argument(
        "--debug",
        action="store_false",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--host-port",
        type=int,
        default=6980,
    )
    parser.add_argument("--host-address", default="0.0.0.0")
    parser.add_argument(
        "streams",
        nargs="+",
        help="Streams in the format of 'address:port/stream_name'",
    )
    parser.add_argument(
        "--output-device",
        type=str,
        help="The name of the output device to use",
    )

    config = parser.parse_args()

    setproctitle("aioVBAN Stream Receiver")
    setup_logging()
    asyncio.run(run_loop(config))
