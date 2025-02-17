import argparse
import asyncio
import sys

import pyaudio
from setproctitle import setproctitle

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import Features
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

async def run_loop(config):
    application_data = VBANApplicationData(
        application_name="VBAN Audio Sender",
        features=Features.Audio | Features.Text,
        device_type=DeviceType.Receptor,
        version="0.2.1",
    )
    client = AsyncVBANClient(application_data=application_data)

    full_address, stream_name = config.stream.split("/")
    if ":" in full_address:
        address, port = full_address.split(":")
    else:
        address = full_address
        port = 6980

    device = client.register_device(address, port)
    stream = await device.text_stream(stream_name)

    await stream.send_text(config.command)


def main():
    parser = argparse.ArgumentParser(
        prog="aioVBAN Text Sender",
        description="Receives Audio Streams from VBAN and plays them back",
    )
    parser.add_argument(
        "--debug",
        action="store_false",
        help="Enable debug logging",
    )
    parser.add_argument(
        "-s",
        "--stream",
        help="Stream in the format of 'address:port/stream_name'",
    )
    parser.add_argument(
        "command",
        help="Command to run",
    )

    config = parser.parse_args()

    setproctitle("aioVBAN Stream Receiver")
    setup_logging()
    asyncio.run(run_loop(config))
