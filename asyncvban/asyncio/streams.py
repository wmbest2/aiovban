import asyncio
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Any

from asyncvban.enums import VBANBaudRate
from asyncvban.packet import VBANPacket
from asyncvban.packet.headers.service import VBANServiceHeader, ServiceType
from asyncvban.packet.headers.text import VBANTextHeader


@dataclass
class VBANStream:
    name: str


@dataclass
class VBANIncomingStream(VBANStream):
    queue_size: int = 100

    _queue: Queue = Queue(maxsize=queue_size)

    async def handle_packet(self, packet: VBANPacket):
        asyncio.create_task(self._queue.put(packet))

    async def get_packet(self) -> VBANPacket:
        return await self._queue.get()


@dataclass
class VBANOutgoingStream(VBANStream):
    _client: Any = None
    _address: str = None
    _port: int = None
    _framecounter: int = field(default=0, init=False)
    _protocol: Any = field(default=None, init=False)

    async def connect(self, address, port, loop=None):
        print("Connect")
        loop = loop or asyncio.get_running_loop()
        self._address = address
        self._port = port
        from asyncvban.asyncio.protocol import VBANSenderProtocol
        _, self._protocol = await loop.create_datagram_endpoint(
            lambda: VBANSenderProtocol(self._client),
            remote_addr=(address, port),
        )

    async def send_packet(self, packet: VBANPacket):
        print("Sending packet with header type ", packet.header.__class__.__name__)
        self._framecounter += 1
        packet.header.framecount = self._framecounter
        self._protocol.send_packet(packet, (self._address, self._port))


@dataclass
class VBANTextStream(VBANOutgoingStream):
    baudrate: VBANBaudRate = VBANBaudRate.RATE_256000

    async def send_text(self, text: str):
        header = VBANTextHeader(baud=self.baudrate)
        await self.send_packet(VBANPacket(header, text.encode()))


@dataclass
class VBANCommandStream(VBANTextStream, VBANIncomingStream):
    update_interval: int = 0xFF

    async def send_renewal_registration(self):
        # Register for updates
        print(f"Registering for updates for {self.update_interval} seconds")
        rt_header = VBANServiceHeader(service=ServiceType.RTPacketRegister, additional_info=self.update_interval)
        await self.send_packet(VBANPacket(rt_header, b""))

    async def renew_updates(self):
        while True:
            await asyncio.sleep(self.update_interval)
            await self.send_renewal_registration()

    async def connect(self, address, port, loop=None):
        await super().connect(address, port, loop)
        await self.send_renewal_registration()
        asyncio.create_task(self.renew_updates())
