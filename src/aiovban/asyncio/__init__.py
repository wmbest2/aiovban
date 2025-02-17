import asyncio
import locale
import logging
import platform
import socket
from dataclasses import dataclass, field
from typing import Any

from .device import VBANDevice
from .streams import VBANOutgoingStream
from .. import VBANApplicationData
from ..packet import ServiceType, VBANPacket
from ..packet.body.service import DeviceType, Features
from ..packet.headers.service import PingFunctions, VBANServiceHeader

logger = logging.getLogger(__name__)


def _default_application_data():
    return VBANApplicationData(
        device_type=DeviceType.Unknown,
        features=Features.NoFeatures,
        version="0.0.1",
        application_name="aiovban",
        lang_code=locale.getdefaultlocale()[0],
    )


@dataclass
class AsyncVBANClient(asyncio.DatagramProtocol):
    application_data: VBANApplicationData = field(default_factory=_default_application_data)
    ignore_audio_streams: bool = True
    default_queue_size: int = 200

    _registered_devices: dict = field(default_factory=dict, repr=False)

    _transport: Any = field(default=None, init=False, repr=False)

    async def listen(self, address="0.0.0.0", port=6980, loop=None):
        loop = loop or asyncio.get_running_loop()

        # Create a socket and set the options
        from .protocol import VBANListenerProtocol

        self._transport, proto = await loop.create_datagram_endpoint(
            lambda: VBANListenerProtocol(self),
            local_addr=(address, port),
            allow_broadcast=not self.ignore_audio_streams,
        )

        return proto.done

    def close(self):
        if self._transport:
            self._transport.close()
            self._transport = None

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

    def quick_reject(self, address):
        return address not in self._registered_devices

    async def process_packet(self, address, port, packet):
        device: VBANDevice = self._registered_devices.get(address)
        if packet.header.streamname == "VBAN Service":
            if packet.header.service == ServiceType.Identification:
                if packet.header.function == PingFunctions.Request:
                    await self.send_ping(address, port, type=PingFunctions.Response)

        if device:
            await device.handle_packet(address, packet)

    async def send_ping(
        self, address, port, type: PingFunctions = PingFunctions.Request
    ):
        print(f"Sending ping to {address}:{port}")
        response_body = self.get_ping_response()
        packet = VBANPacket(
            header=VBANServiceHeader(
                streamname="VBAN Service",
                service=ServiceType.Identification,
                function=type,
            ),
            body=response_body.pack(),
        )
        logger.info(f"Sending ping response {response_body}")
        out_stream = VBANOutgoingStream(name="VBAN Service", _client=self)
        await out_stream.connect(address, port)
        await out_stream.send_packet(packet)

    def register_device(self, address: str, port: int = 6980):
        ip_address = socket.gethostbyname(address)
        if ip_address in self._registered_devices:
            return self._registered_devices[ip_address]

        self._registered_devices[ip_address] = VBANDevice(
            address=ip_address,
            default_port=port,
            _client=self,
            default_stream_size=self.default_queue_size,
        )
        return self._registered_devices[ip_address]

    def devices(self):
        return list(self._registered_devices.values())
