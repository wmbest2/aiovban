import asyncio
import logging
from asyncio import Future
from dataclasses import dataclass, field
from typing import Any

from . import AsyncVBANClient
from ..packet import VBANPacket
from ..packet.headers import VBANHeaderException


logger = logging.getLogger(__package__)


@dataclass
class VBANBaseProtocol(asyncio.DatagramProtocol):
    client: AsyncVBANClient

    done: Future = asyncio.get_event_loop().create_future()

    def connection_made(self, transport):
        pass

    def datagram_received(self, data, addr):
        pass

    def error_received(self, exc):
        self.done.set_exception(exc)

    def connection_lost(self, exc):
        if self.done.done():
            return
        self.done.set_exception(exc)


@dataclass
class VBANListenerProtocol(VBANBaseProtocol):
    loop: asyncio.BaseEventLoop = asyncio.get_running_loop()

    def connection_made(self, transport):
        logger.info(f"Connection made to {transport}")

    def datagram_received(self, data, addr):
        try:
            if self.client.quick_reject(addr[0]):
                return
            packet = VBANPacket.unpack(data)
            asyncio.create_task(self.client.process_packet(addr[0], addr[1], packet))
        except VBANHeaderException as e:
            logger.info(f"Error unpacking packet: {e}")


@dataclass
class VBANSenderProtocol(VBANBaseProtocol):
    _transport: Any = field(default=None, init=False)

    def connection_made(self, transport):
        self._transport = transport
        logger.info(f"Connection made to {transport.get_extra_info('peername')}")

    def send_packet(self, data: VBANPacket, addr):
        if self._transport:
            self._transport.sendto(data.pack(), addr)

    def connection_lost(self, exc):
        self._transport = None
        super().connection_lost(exc)
