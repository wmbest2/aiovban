import asyncio
import logging
import platform
from aiovban.asyncio import AsyncVBANClient
from aiovban.packet.headers.service import PingFunctions
from aiovban.packet.body.service import Ping
from aiovban.packet import VBANPacket

logging.basicConfig(level=logging.INFO)

async def capture_ping():
    client = AsyncVBANClient()
    # Start listening to receive the response
    # We need to listen on the port we expect the response on, 
    # but VBAN usually responds to the source port.
    # AsyncVBANClient.listen() binds to a port.
    
    await client.listen(port=6980) # Bind to standard port
    port = client._transport.get_extra_info('sockname')[1]
    print(f"Listening on ephemeral port {port}")
    
    target_ip = "192.168.10.114"
    target_port = 6980
    
    device = await client.register_device(target_ip, target_port)
    
    # We want to capture the packet. We can override process_packet or just look at the device
    original_process_packet = client.process_packet
    captured_packet = None
    captured_addr = None
    
    event = asyncio.Event()

    async def hooked_process_packet(address, port, packet):
        nonlocal captured_packet, captured_addr
        from aiovban.packet.headers.service import VBANServiceHeader
        if isinstance(packet.header, VBANServiceHeader):
            print(f"Received SERVICE packet from {address}:{port}")
            captured_packet = packet
            captured_addr = (address, port)
            event.set()
        await original_process_packet(address, port, packet)

    client.process_packet = hooked_process_packet

    print(f"Sending ping to {target_ip}:{target_port}...")
    await client.send_ping(target_ip, target_port)

    try:
        await asyncio.wait_for(event.wait(), timeout=5.0)
        print("Captured packet!")
        print(f"Header: {captured_packet.header}")
        if isinstance(captured_packet.body, bytes):
             ping_body = Ping.unpack(captured_packet.body)
        else:
             ping_body = captured_packet.body
        
        print(f"Ping Body: {ping_body}")
        
        # Also print raw bytes of the body if we can reconstruct it
        raw_body = ping_body.pack()
        print(f"Raw body hex: {raw_body.hex()}")
        
        full_packet = VBANPacket(header=captured_packet.header, body=raw_body)
        print(f"Full packet hex: {full_packet.pack().hex()}")
        
    except asyncio.TimeoutError:
        print("Timed out waiting for ping response")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(capture_ping())
