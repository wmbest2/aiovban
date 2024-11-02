import asyncio
from asyncio import Queue
from asyncvban.packet import VBANPacket


class AsyncVBANReceiver:
    def __init__(self, host: str, port: int, queue_size: int = 10, queue: Queue = None):
        self.host = host
        self.port = port
        self.queue = queue or Queue(maxsize=queue_size)
        self.transport = None

    async def connect(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(self.host, self.port)
        )

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.raw_queue.put_nowait((data, addr))

    def error_received(self, exc):
        print(f"Error received: {exc}")

    def connection_lost(self, exc):
        print("Connection closed")
        self.transport = None

    async def receive_packet(self) -> VBANPacket:
        return await self.queue.get()

    async def close(self):
        if self.transport:
            self.transport.close()