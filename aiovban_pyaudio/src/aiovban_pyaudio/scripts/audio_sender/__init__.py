import argparse
import asyncio
import logging
import sys

import pyaudio

from aiovban import VBANApplicationData, DeviceType, VBANSampleRate
from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import Features
from ..util import get_device_by_name, setproctitle
from ... import VBANAudioSender, __version__

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


async def run_loop(config):
    application_data = VBANApplicationData(
        application_name="VBAN Audio Sender",
        features=Features.Audio | Features.Text,
        device_type=DeviceType.Transmitter,
        version=__version__,
    )
    client = AsyncVBANClient(application_data=application_data)

    pyaudio_instance = pyaudio.PyAudio()

    input_device = get_device_by_name(pyaudio_instance, config.input_device)

    device = await client.register_device(config.address, config.port)
    logger.info(f"Registered device {device}")
    stream = await device.send_stream(config.stream_name)

    sample_rate = VBANSampleRate.find(config.sample_rate)
    if not sample_rate:
        logger.error(f"Invalid sample rate: {config.sample_rate}")
        return

    listener = VBANAudioSender(
        stream=stream,
        pyaudio=pyaudio_instance,
        device_index=input_device,
        channels=config.channels,
        sample_rate=VBANSampleRate.find(config.sample_rate),
        framebuffer_size=config.framebuffer_size,
    )
    await listener.listen()


def main():
    parser = argparse.ArgumentParser(
        prog="aioVBAN Stream Sender",
        description="Captures audio from an input device and sends it via VBAN",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
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
        help="The name of the input device to use",
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
    parser.add_argument(
        "--framebuffer-size",
        type=int,
        default=256,
        help="Number of frames per VBAN packet",
    )

    config = parser.parse_args()

    setproctitle("aioVBAN Stream Sender")
    setup_logging(config.debug)
    asyncio.run(run_loop(config))
