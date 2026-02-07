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
    done: Future = field(default=None, init=False)

    def connection_made(self, transport):
        # Create future in async context when protocol is established
        loop = asyncio.get_running_loop()
        self.done = loop.create_future()

    def datagram_received(self, data, addr):
        pass

    def error_received(self, exc):
        if self.done and not self.done.done():
            self.done.set_exception(exc)

    def connection_lost(self, exc):
        if not self.done:
            return
        if self.done.done():
            return
        if exc:
            self.done.set_exception(exc)
        else:
            self.done.set_result(exc)


@dataclass
class VBANListenerProtocol(VBANBaseProtocol):
    pending_tasks: set = field(default_factory=set, init=False)

    def connection_made(self, transport):
        super().connection_made(transport)
        logger.info(f"Connection made to {transport}")

    def datagram_received(self, data, addr):
        try:
            if self.client.quick_reject(addr[0]):
                return
            packet = VBANPacket.unpack(data)
            task = asyncio.create_task(self.client.process_packet(addr[0], addr[1], packet))
            # Track task and add callback to remove it when done
            self.pending_tasks.add(task)
            task.add_done_callback(self.pending_tasks.discard)
        except (VBANHeaderException, ValueError) as e:
            logger.info(f"Error unpacking packet: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing packet: {e}")


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
