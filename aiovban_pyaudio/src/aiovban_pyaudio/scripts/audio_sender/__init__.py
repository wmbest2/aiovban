import argparse
import asyncio
import logging
import sys

import pyaudio

from aiovban import VBANApplicationData, DeviceType, VBANSampleRate
from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import Features
from ..util import get_device_by_name, setproctitle
from ... import VBANAudioSender

logger = logging.getLogger(__name__)


def setup_logging(debug=False):
    import logging

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


async def wait_for_first_done(*tasks):
    # Wrap coroutines in tasks, as asyncio.wait() requires tasks/futures since Python 3.11
    wrapped = [asyncio.ensure_future(t) for t in tasks]
    (done_tasks, pending) = await asyncio.wait(
        wrapped, return_when=asyncio.FIRST_COMPLETED
    )
    for pending_task in pending:
        pending_task.cancel()
    return done_tasks


async def run_loop(config):
    application_data = VBANApplicationData(
        application_name="VBAN Audio Sender",
        features=Features.Audio | Features.Text,
        device_type=DeviceType.Receptor,
        version="0.2.1",
    )
    client = AsyncVBANClient(application_data=application_data)

    pyaudio_instance = pyaudio.PyAudio()

    input_device = get_device_by_name(pyaudio_instance, config.input_device)

    device = await client.register_device(config.address, config.port)
    logger.info(f"Registered device {device}")
    stream = await device.send_stream(config.stream_name)

    listener = VBANAudioSender(
        stream=stream,
        pyaudio=pyaudio_instance,
        device_index=input_device,
        channels=config.channels,
        sample_rate=VBANSampleRate.find(config.sample_rate),
    )
    await listener.listen()


def main():
    parser = argparse.ArgumentParser(
        prog="aioVBAN Stream Sender",
        description="Receives Audio Streams from VBAN and plays them back",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--address",
        type=str,
        help="The address to send the VBAN packets to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6980,
    )
    parser.add_argument(
        "--input-device",
        type=str,
        help="The name of the output device to use",
    )
    parser.add_argument(
        "--stream-name",
        type=str,
        help="The name of the stream to send",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=2,
        help="Number of channels to use",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        help="Sample rate to use",
    )

    config = parser.parse_args()

    setproctitle("aioVBAN Stream Sender")
    setup_logging(config.debug)
    asyncio.run(run_loop(config))
