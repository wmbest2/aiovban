import asyncio
import logging
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Any

from ..enums import VBANBaudRate, BackPressureStrategy
from ..packet import VBANPacket
from ..packet.body import Utf8StringBody
from ..packet.headers.service import VBANServiceHeader, ServiceType
from ..packet.headers.text import VBANTextHeader


logger = logging.getLogger(__package__)


@dataclass
class VBANStream:
    name: str


@dataclass
class VBANIncomingStream(VBANStream):
    queue_size: int = 100

    _back_pressure_strategy: BackPressureStrategy = field(
        default=BackPressureStrategy.DROP
    )
    _queue: Queue = field(default_factory=Queue, init=False)
    _mutex: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(self.queue_size)

    async def handle_packet(self, packet: VBANPacket):
        if self._back_pressure_strategy in [
            BackPressureStrategy.DROP,
            BackPressureStrategy.RAISE,
        ]:
            try:
                self._queue.put_nowait(packet)
                return
            except asyncio.QueueFull:
                if self._back_pressure_strategy == BackPressureStrategy.RAISE:
                    raise asyncio.QueueFull
                else:
                    logger.debug(f"Queue full for stream {self.name}. Dropping packet")
                    return

        if self._back_pressure_strategy == BackPressureStrategy.DRAIN_OLDEST:
            await self._drain_queue()

        asyncio.create_task(self._queue.put(packet))

    async def _drain_queue(self):
        # Leveraging the mutex to ensure that we don't have multiple drain operations happening at the same time
        await self._mutex.acquire()
        for i in range(int(self.queue_size / 2)):
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._mutex.release()
        logger.debug(
            f"Drained {int(self.queue_size / 2)} packets from stream {self.name}"
        )

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
        loop = loop or asyncio.get_running_loop()
        self._address = address
        self._port = port
        from .protocol import VBANSenderProtocol

        _, self._protocol = await loop.create_datagram_endpoint(
            lambda: VBANSenderProtocol(self._client),
            remote_addr=(address, port),
        )

    async def send_packet(self, packet: VBANPacket):
        logger.debug(
            f"Sending packet with header type {packet.header.__class__.__name__}"
        )
        self._framecounter += 1
        packet.header.framecount = self._framecounter
        self._protocol.send_packet(packet, (self._address, self._port))


@dataclass
class VBANTextStream(VBANOutgoingStream):
    baudrate: VBANBaudRate = VBANBaudRate.RATE_256000

    async def send_text(self, text: str):
        header = VBANTextHeader(baud=self.baudrate)
        await self.send_packet(VBANPacket(header, Utf8StringBody(text)))


@dataclass
class VBANRTStream(VBANOutgoingStream, VBANIncomingStream):
    automatic_renewal: bool = True
    update_interval: int = 0xFF

    async def register_for_updates(self):
        # Register for updates
        logger.info(f"Registering for updates for {self.update_interval} seconds")
        rt_header = VBANServiceHeader(
            service=ServiceType.RTPacketRegister, additional_info=self.update_interval
        )
        registraiton_expiry = asyncio.Future()

        async def start_expiry_timer():
            await asyncio.sleep(self.update_interval)
            registraiton_expiry.set_result(None)

        await self.send_packet(VBANPacket(rt_header))
        asyncio.create_task(start_expiry_timer())
        return registraiton_expiry

    async def renew_updates(self):
        while True:
            waiter = await self.register_for_updates()
            await waiter

    async def handle_packet(self, packet: VBANPacket):
        header = packet.header
        if (
            isinstance(header, VBANServiceHeader)
            and header.service == ServiceType.RTPacket
        ):
            await super().handle_packet(packet)
        else:
            logger.info(
                f"Received packet for RTStream with incorrect header type {header}"
            )

    async def connect(self, address, port, loop=None):
        await super().connect(address, port, loop)
        if self.automatic_renewal:
            asyncio.create_task(self.renew_updates())
