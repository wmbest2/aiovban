import asyncio
import argparse
import logging
from aiovban import VBANApplicationData, DeviceType, Features
from aiovban.asyncio import AsyncVBANClient
from aiovban.packet import VBANPacket
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0, RTPacketBodyType1

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def _print_packet(count, address, port, packet):
    print(f"\n--- RT Packet #{count} from {address}:{port} ---")
    print(f"Function (Type): {packet.header.function}")

    if isinstance(packet.body, RTPacketBodyType0):
        b = packet.body
        print(f"Type 0 — Voicemeeter {b.voice_meeter_type.name} v{b.voice_meeter_version}")
        for i, s in enumerate(b.strips[:2]):
            print(f"  Strip[{i}] Label: {s.label:<10} | State: {s.state.value:#010x} | Gain: {s.layers[0]/100.0:.1f} dB")
    elif isinstance(packet.body, RTPacketBodyType1):
        b = packet.body
        print(f"Type 1 — Voicemeeter {b.voice_meeter_type.name} v{b.voice_meeter_version}")
        for i, s in enumerate(b.strips[:2]):
            print(f"  Strip[{i}] dblevel: {s.dblevel/100.0:.1f} dB | mode: {s.mode:#010x}")
    else:
        print(f"Unknown body type: {type(packet.body).__name__}")

    # Hex dump of first 128 body bytes — highlights 0x0A/0x14/0x1E
    try:
        raw_body = packet.body.pack()
    except (NotImplementedError, Exception):
        raw_body = None

    if raw_body is not None:
        targets = {0x0A, 0x14, 0x1E}
        print(f"Body: {len(raw_body)} bytes")
        for i in range(0, min(128, len(raw_body)), 16):
            chunk = raw_body[i:i+16]
            hex_parts = []
            has_target = False
            for byte in chunk:
                s = f"{byte:02x}"
                if byte in targets:
                    s = f"[{s}]"
                    has_target = True
                else:
                    s = f" {s} "
                hex_parts.append(s)
            if has_target or i < 64:
                ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                print(f"  {i:04x}: {''.join(hex_parts):<64} | {ascii_str}")


class RTPacketInspector(AsyncVBANClient):
    def __init__(self, target_address, *args, **kwargs):
        app_data = VBANApplicationData(
            application_name="aiovban-inspector",
            features=Features.Audio | Features.Text,
            device_type=DeviceType.Receptor,
            version="1.1.0"
        )
        kwargs['application_data'] = app_data
        super().__init__(*args, **kwargs)
        self.target_address = target_address

    def quick_reject(self, address):
        return address != self.target_address

async def main():
    parser = argparse.ArgumentParser(description="VBAN RT Packet Inspector")
    parser.add_argument("address", help="IP address of the remote VBAN device")
    parser.add_argument("--remote-port", type=int, default=6980, help="Remote VBAN port (default: 6980)")
    parser.add_argument("--local-port", type=int, default=6981, help="Local port (default: 6981)")
    parser.add_argument("--interval", type=int, default=0xFF, help="Update interval (default: 0xFF)")
    parser.add_argument("--timeout", type=int, default=15, help="Total timeout in seconds (default: 15)")
    
    args = parser.parse_args()

    client = RTPacketInspector(args.address, ignore_audio_streams=True)
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
        # Register for Type 0 updates (auto-renewed by rt_stream)
        rt_stream = await device.rt_stream(update_interval=args.interval)

        # Also register for Type 1 updates and renew on the same cadence.
        async def renew_type1():
            while True:
                rt1_header = VBANServiceHeader(
                    service=ServiceType.RTPacketRegister,
                    function=0x01,
                    additional_info=args.interval,
                )
                client.send_datagram(VBANPacket(rt1_header).pack(), (args.address, args.remote_port))
                await asyncio.sleep(args.interval)

        asyncio.create_task(renew_type1())
        print(f"Registered for Type 0 and Type 1 RT packets (interval={args.interval}s)")

        # Drain packets directly from the stream queue — the fast path in
        # datagram_received bypasses process_packet, so we must consume here.
        packet_count = 0
        type1_count = 0
        deadline = asyncio.get_event_loop().time() + args.timeout
        print(f"Waiting up to {args.timeout}s for packets...")
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            try:
                packet = await asyncio.wait_for(rt_stream.get_packet(), timeout=min(1.0, remaining))
            except asyncio.TimeoutError:
                continue
            packet_count += 1
            if isinstance(packet.body, RTPacketBodyType1):
                type1_count += 1
            # Print Type 1 always; suppress repeated Type 0 after the first few
            if isinstance(packet.body, RTPacketBodyType1) or packet_count <= 3:
                _print_packet(packet_count, args.address, args.remote_port, packet)

        print(f"\nDone. Type 0: {packet_count - type1_count}  Type 1: {type1_count}  Raw UDP: {client.raw_packets_received}")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, RuntimeError):
        pass
