import asyncio
import socket
from aiovban.packet import VBANPacket
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType, PingFunctions

async def test_send():
    header = VBANServiceHeader(
        streamname="VBAN Service",
        service=ServiceType.Identification,
        function=PingFunctions.Request
    )
    # Body is not strictly necessary for simple ping request, or can be empty
    packet = VBANPacket(header, b"")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # VBAN normally expects ping on 6980, but our helper is on 6981 for testing
    sock.sendto(packet.pack(), ("127.0.0.1", 6981))
    sock.close()
    print("Test ping sent to 6981.")

if __name__ == "__main__":
    asyncio.run(test_send())
