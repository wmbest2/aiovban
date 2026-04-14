import asyncio
import argparse
import logging
import struct
from aiovban import VBANApplicationData, DeviceType, Features
from aiovban.asyncio import AsyncVBANClient
from aiovban.packet import VBANPacket
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class RTPacketInspector(AsyncVBANClient):
    def __init__(self, target_address, *args, **kwargs):
        # Identify as a proper Receptor to encourage VoiceMeeter to talk to us
        app_data = VBANApplicationData(
            application_name="aiovban-inspector",
            features=Features.Audio | Features.Text,
            device_type=DeviceType.Receptor,
            version="1.1.0"
        )
        kwargs['application_data'] = app_data
        super().__init__(*args, **kwargs)
        self.target_address = target_address
        self.packet_count = 0

    def quick_reject(self, address):
        return address != self.target_address

    async def process_packet(self, address, port, packet):
        # Call super to ensure device state is updated and handle_packet is called
        await super().process_packet(address, port, packet)

        if not isinstance(packet.header, VBANServiceHeader):
            return
            
        print(f"DEBUG: Received Service Packet type {packet.header.service} function {packet.header.function}")

        if packet.header.service != ServiceType.RTPacket:
            return

        self.packet_count += 1
        print(f"\n--- RT Packet #{self.packet_count} from {address}:{port} ---")
        print(f"Header Function (Type): {packet.header.function}")
        
        # RTPacketBodyType0 objects have a pack() method
        if hasattr(packet.body, 'pack'):
            raw_body = packet.body.pack()
        else:
            raw_body = bytes(packet.body)
        
        print(f"Body Length: {len(raw_body)} bytes")
        
        # Look for values 10, 20, 30 (0x0A, 0x14, 0x1E)
        targets = [0x0A, 0x14, 0x1E]
        
        limit = len(raw_body)
        for i in range(0, limit, 16):
            chunk = raw_body[i:i+16]
            hex_parts = []
            has_target = False
            for b in chunk:
                s = f"{b:02x}"
                if b in targets:
                    s = f"[{s}]" # Highlight potential matches
                    has_target = True
                else:
                    s = f" {s} "
                hex_parts.append(s)
            
            if has_target or (i < 256): # Always show first few rows, or rows with targets
                hex_str = "".join(hex_parts)
                ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                print(f"{i:04x}: {hex_str:<64} | {ascii_str}")

        if self.packet_count >= 10:
            print("\nCaptured 10 packets. Stopping...")
            self.close()

async def main():
    parser = argparse.ArgumentParser(description="VBAN RT Packet Inspector")
    parser.add_argument("address", help="IP address of the remote VBAN device")
    parser.add_argument("--remote-port", type=int, default=6980, help="Remote VBAN port (default: 6980)")
    parser.add_argument("--local-port", type=int, default=6981, help="Local port (default: 6981)")
    parser.add_argument("--interval", type=int, default=0xFF, help="Update interval (default: 0xFF)")
    parser.add_argument("--timeout", type=int, default=15, help="Total timeout in seconds (default: 15)")
    
    args = parser.parse_args()

    client = RTPacketInspector(args.address, ignore_audio_streams=False)
    try:
        await client.listen(address="0.0.0.0", port=args.local_port)
        print(f"Local listener bound to 0.0.0.0:{args.local_port}")
    except OSError:
        print(f"Port {args.local_port} busy, falling back to auto-assign...")
        await client.listen(address="0.0.0.0", port=0)
        local_addr = client._transport.get_extra_info("sockname")
        print(f"Local listener bound to {local_addr[0]}:{local_addr[1]}")
    
    print(f"Registering for RT updates from {args.address}...")
    try:
        device = await client.register_device(args.address, args.remote_port)
        # Register for updates
        await device.rt_stream(update_interval=args.interval)
        
        print(f"Waiting up to {args.timeout}s for packets...")
        start_time = asyncio.get_event_loop().time()
        while client.packet_count < 10 and (asyncio.get_event_loop().time() - start_time) < args.timeout:
            await asyncio.sleep(0.5)
            
        if client.packet_count == 0:
            print(f"\nTimed out after {args.timeout}s without receiving any packets.")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, RuntimeError):
        pass
