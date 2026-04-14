import asyncio
import logging
from asyncio import Queue
from dataclasses import dataclass, field
from optparse import Option
from typing import Any, Union, Optional

from .util import BackPressureQueue, BackPressureStrategy
from ..enums import VBANBaudRate
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
    back_pressure_strategy: BackPressureStrategy = BackPressureStrategy.DROP
    _queue: BackPressureQueue = field(default=None, init=False)

    def __post_init__(self):
        self._queue = BackPressureQueue(
            queue_size=self.queue_size,
            queue_name=self.name,
            back_pressure_strategy=self.back_pressure_strategy,
        )

    async def handle_packet(self, packet: VBANPacket):
        await self._queue.put(packet)

    def handle_packet_nowait(self, packet: VBANPacket) -> bool:
        return self._queue.put_nowait(packet)

    async def get_packet(self) -> VBANPacket:
        return await self._queue.get()

    def get_packet_nowait(self) -> Optional[VBANPacket]:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None


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
        self.send_packet_sync(packet)

    def send_packet_sync(self, packet: VBANPacket):
        self._framecounter += 1
        packet.header.framecount = self._framecounter
        if self._protocol:
            self._protocol.send_packet(packet, (self._address, self._port))


@dataclass
class BufferedVBANOutgoingStream(VBANOutgoingStream):
    buffer_size: int = 100
    back_pressure_strategy: BackPressureStrategy = BackPressureStrategy.BLOCK

    _buffer: BackPressureQueue = field(default=None, init=False)
    send_task: Any = field(default=None, init=False)

    def __post_init__(self):
        self._buffer = BackPressureQueue(
            queue_size=self.buffer_size,
            queue_name=self.name,
            back_pressure_strategy=self.back_pressure_strategy,
        )

    async def connect(self, address, port, loop=None):
        await super().connect(address, port, loop)
        self.send_task = asyncio.create_task(self._send_buffered_packets_wrapper())

    async def _send_buffered_packets_wrapper(self):
        """Wrapper to handle exceptions in the background task"""
        try:
            await self.send_buffered_packets()
        except Exception as e:
            logger.error(f"Error in send_buffered_packets for {self.name}: {e}")
            raise

    async def send_packet(self, packet: VBANPacket):
        await self._buffer.put(packet)

    def send_packet_nowait(self, packet: VBANPacket) -> bool:
        """Synchronously put a packet into the outgoing buffer."""
        return self._buffer.put_nowait(packet)

    def send_packet_threadsafe(self, packet: VBANPacket, loop: asyncio.AbstractEventLoop) -> None:
        """Thread-safely put a packet into the outgoing buffer."""
        self._buffer.put_threadsafe(packet, loop)

    async def send_buffered_packets(self):
        while True:
            packet = await self._buffer.get()
            self.send_packet_sync(packet)


@dataclass
class VBANTextStream(VBANOutgoingStream):
    baud_rate: VBANBaudRate = VBANBaudRate.RATE_256000

    async def send_text(self, text: str):
        header = VBANTextHeader(baud=self.baud_rate, streamname=self.name)
        await self.send_packet(VBANPacket(header, Utf8StringBody(text)))


@dataclass
class VBANRTStream(VBANOutgoingStream, VBANIncomingStream):
    automatic_renewal: bool = True
    update_interval: int = 0xFF
    renewal_task: Any = field(default=None, init=False)
    pending_timers: set = field(default_factory=set, init=False)

    async def register_for_updates(self):
        # Register for updates
        logger.info(f"Registering for updates for {self.update_interval} seconds")
        rt_header = VBANServiceHeader(
            service=ServiceType.RTPacketRegister, 
            additional_info=self.update_interval
        )
        registration_expiry = asyncio.Future()

        async def start_expiry_timer():
            try:
                await asyncio.sleep(self.update_interval)
                if not registration_expiry.done():
                    registration_expiry.set_result(None)
            except Exception as e:
                logger.error(f"Error in expiry timer: {e}")
                if not registration_expiry.done():
                    registration_expiry.set_exception(e)

        # Send via the client's listener socket so VoiceMeeter replies to our listening port
        self._framecounter += 1
        packet = VBANPacket(rt_header)
        packet.header.framecount = self._framecounter
        self._client.send_datagram(packet.pack(), (self._address, self._port))
        timer_task = asyncio.create_task(start_expiry_timer())
        self.pending_timers.add(timer_task)
        timer_task.add_done_callback(self.pending_timers.discard)
        return registration_expiry

    async def renew_updates(self):
        try:
            while True:
                waiter = await self.register_for_updates()
                await waiter
        except Exception as e:
            logger.error(f"Error in renew_updates: {e}")
            raise

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
            self.renewal_task = asyncio.create_task(self.renew_updates())

    async def close(self):
        """Stop the renewal task and clear any pending timers."""
        if self.renewal_task:
            self.renewal_task.cancel()
            try:
                await self.renewal_task
            except asyncio.CancelledError:
                pass
            self.renewal_task = None
        
        for timer in list(self.pending_timers):
            timer.cancel()
        self.pending_timers.clear()


@dataclass
class VBANChatStream(VBANOutgoingStream, VBANIncomingStream):
    async def send_chat(self, text: str):
        """Send a chat message using the Chat_UTF8 service."""
        header = VBANServiceHeader(
            service=ServiceType.Chat_UTF8,
            streamname=self.name
        )
        await self.send_packet(VBANPacket(header, Utf8StringBody(text + "\0")))

    async def get_chat(self) -> str:
        """Wait for and return the next chat message text."""
        packet = await self.get_packet()
        if isinstance(packet.body, Utf8StringBody):
            return packet.body.text.strip("\0")
        return str(packet.body)

    async def handle_packet(self, packet: VBANPacket):
        header = packet.header
        if (
            isinstance(header, VBANServiceHeader)
            and header.service == ServiceType.Chat_UTF8
        ):
            await super().handle_packet(packet)
