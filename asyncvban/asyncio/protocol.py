import asyncio
from asyncio import Future
from dataclasses import dataclass, field
from typing import Any

from asyncvban.asyncio import AsyncVBANClient
from asyncvban.packet import VBANPacket


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
        self.done.set_result(None)


@dataclass
class VBANListenerProtocol(VBANBaseProtocol):
    loop: asyncio.BaseEventLoop = asyncio.get_running_loop()

    def connection_made(self, transport):
        print(f"Connection made to {transport}")

    def datagram_received(self, data, addr):
        packet = VBANPacket.unpack(data)
        asyncio.create_task(self.client.process_packet(addr[0], packet))

@dataclass
class VBANSenderProtocol(VBANBaseProtocol):
    _transport: Any = field(default=None, init=False)

    def connection_made(self, transport):
        self._transport = transport
        print(f"Connection made to {transport.get_extra_info('peername')}")

    def send_packet(self, data: VBANPacket, addr):
        if self._transport:
            self._transport.sendto(data.pack(), addr)

    def connection_lost(self, exc):
        self._transport = None
        super().connection_lost(exc)