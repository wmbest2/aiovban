import asyncio
from asyncio import Queue
import socket
from dataclasses import dataclass, field
from typing import Any

from asyncvban.packet import VBANPacket

@dataclass
class VBANStream:
    name: str
    sender: str
    queue_size: int = 100

    _queue: Queue = Queue(maxsize=queue_size)

@dataclass
class VBANCommandStream(VBANStream):
    pass


@dataclass
class AsyncVBANClient(asyncio.DatagramProtocol):
    host: str
    port: int
    queue_size: int = 100
    queue: Queue = Queue(maxsize=queue_size)
    command_stream: str = None
    audio_streams_in: [str] = field(default_factory=list)

    _frame_counter: int = 0
    _transport: Any = field(default=None, init=False)

    async def connect(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        print(socket.gethostbyname(self.host))

        local_addr = None
        if any([self.command_stream, *self.audio_streams_in]):
            local_addr = ('0.0.0.0', self.port)

        # Create a socket and set the options
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: self,
                remote_addr=(self.host, self.port),
                local_addr=local_addr,
                allow_broadcast=local_addr is not None
            )
        except:
            print("Failed to connect")

    def connection_made(self, transport):
        self._transport = transport

    async def process_packet(self, data):
        packet = VBANPacket.unpack(data)
        if packet.header.streamname == self.command_stream or packet.header.streamname in self.audio_streams_in:
            asyncio.create_task(self.queue.put(packet))

    def datagram_received(self, data, addr):
        asyncio.create_task(self.process_packet(data))

    def error_received(self, exc):
        print(f"Error received: {exc}")

    def connection_lost(self, exc):
        print("Connection closed")
        self._transport = None

    async def send_packet(self, packet: VBANPacket):
        if self._transport:
            self._frame_counter += 1
            packet.header.framecount = self._frame_counter
            self._transport.sendto(packet.pack())

    async def receive_packet(self) -> VBANPacket:
        return await self.queue.get()

    async def close(self):
        if self._transport:
            self._transport.close()

    class ReceivedPacket:
        def __init__(self, packet: VBANPacket, sender: tuple):
            self.packet = packet
            self.sender = sender