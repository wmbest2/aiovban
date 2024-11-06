import asyncio
import dataclasses
import locale
import logging
import platform
import socket
from dataclasses import dataclass, field
from typing import Any

from .device import VBANDevice
from .. import VBANApplicationData
from ..packet.body.service import DeviceType, Features

logger = logging.getLogger(__name__)


@dataclass
class AsyncVBANClient(asyncio.DatagramProtocol):
    application_data: VBANApplicationData = VBANApplicationData(
        device_type=DeviceType.Unknown,
        features=Features.NoFeatures,
        version="0.0.1",
        application_name="aiovban",
        lang_code=locale.getdefaultlocale()[0],
    )
    ignore_audio_streams: bool = True
    default_queue_size: int = 200

    _registered_devices: dict = field(default_factory=dict)

    _transport: Any = field(default=None, init=False)

    async def listen(self, address="0.0.0.0", port=6980, loop=None):
        loop = loop or asyncio.get_running_loop()

        # Create a socket and set the options
        try:
            from .protocol import VBANListenerProtocol

            _, proto = await loop.create_datagram_endpoint(
                lambda: VBANListenerProtocol(self),
                local_addr=(address, port),
                allow_broadcast=not self.ignore_audio_streams,
            )

            await proto.done
        except Exception as e:
            print("Failed to connect")
            print(e)

    @staticmethod
    def _get_device_name():
        name = platform.system()
        if name == "Darwin":
            name = "MacOS"
        elif not name:
            name = "Unknown"
        return f"{name} Device"

    def get_ping_response(self):
        from ..packet.body.service import Ping

        return Ping(
            **self.application_data.__dict__,
            device_name=self._get_device_name(),
            host_name=platform.node(),
        )

    async def process_packet(self, address, packet):
        device: VBANDevice = self._registered_devices.get(address)
        if device:
            await device.handle_packet(address, packet)

    def register_device(self, address: str, port: int = 6980):
        ip_address = socket.gethostbyname(address)
        self._registered_devices[ip_address] = VBANDevice(
            ip_address, port, _client=self, default_stream_size=self.default_queue_size
        )
        return self._registered_devices[ip_address]

    def devices(self):
        return list(self._registered_devices.values())
