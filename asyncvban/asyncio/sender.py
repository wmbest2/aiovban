import asyncio
from asyncvban.packet import VBANPacket

class AsyncVBANSender:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.transport = None

    async def connect(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            remote_addr=(self.host, self.port)
        )

    def connection_made(self, transport):
        self.transport = transport

    def error_received(self, exc):
        print(f"Error received: {exc}")

    def connection_lost(self, exc):
        print("Connection closed")
        self.transport = None

    async def send_packet(self, packet: VBANPacket):
        if self.transport:
            self.transport.sendto(packet.pack())

    async def close(self):
        if self.transport:
            self.transport.close()