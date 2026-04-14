import socket
import struct
import sys
import time
from collections import Counter

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 6980
REGISTER_HOST = sys.argv[2] if len(sys.argv) > 2 else None

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("0.0.0.0", PORT))
except OSError:
    sock.bind(("0.0.0.0", 0))
    print(f"Port busy, bound to {sock.getsockname()[1]}")

sock.settimeout(2)
print(f"Listening on {sock.getsockname()}")

def send_reg(func, payload, name=b"VBAN Service"):
    name_bytes = name.ljust(16, b"\x00")
    # FOURC (4) + Protocol/SR (1) + Function (1) + Service (1) + Addit (1) + Stream (16) + Frame (4)
    header = b"VBAN" + bytes([0x60, func, 0x20, 0xFF]) + name_bytes + struct.pack("<L", 0)
    sock.sendto(header + payload, (REGISTER_HOST, 6980))
    print(f"Sent Reg: Func={func}, Name='{name.decode()}', Payload={payload.hex()}")

if REGISTER_HOST:
    # 1. Send Ping
    ping_header = b"VBAN" + bytes([0x60, 0x00, 0x00, 0x00]) + b"VBAN Service\x00\x00\x00\x00" + struct.pack("<L", 0)
    sock.sendto(ping_header + b"\x00"*128, (REGISTER_HOST, 6980))
    print(f"Sent Ping to {REGISTER_HOST}")
    time.sleep(0.1)

    # 2. Register for Type 0 (level/state) and Type 1 (strip params) RT packets
    bitmask = b"\x06" + b"\x00" * 15 # IDs 1 and 2
    send_reg(0, b"", b"VBAN Service")
    send_reg(0, bitmask, b"VBAN Service")
    send_reg(0, bitmask, b"VMRT")
    send_reg(0, bitmask, b"Register RTP")
    send_reg(1, b"", b"VBAN Service")
    send_reg(1, bitmask, b"VBAN Service")

print("Capturing for 30 seconds...")
counts = Counter()
start_time = time.time()
try:
    while time.time() - start_time < 30:
        try:
            data, addr = sock.recvfrom(4096)
            if data[:4] != b"VBAN": continue
            protocol = data[4] & 0xE0
            if protocol != 0x60: continue
            
            # Service 33 is RTPacket
            if data[6] == 33:
                fid = data[5]
                counts[fid] += 1
                if fid != 0:
                    print(f"\n*** INTERESTING PACKET! Type {fid} Size {len(data)} ***")
                    print(f"Header: {data[:28].hex()}")
                    # Dump first 64 bytes of body
                    body = data[28:]
                    for i in range(0, min(128, len(body)), 16):
                        row = body[i:i+16]
                        print(f"{i:04x}: {' '.join(f'{b:02x}' for b in row)}")

        except socket.timeout:
            # Periodically re-register every 5 seconds
            if REGISTER_HOST and int(time.time() - start_time) % 5 == 0:
                send_reg(0, b"\x00\x01\x02", b"VBAN Service")
                send_reg(1, b"\x00\x01\x02", b"VBAN Service")
            continue
except KeyboardInterrupt:
    pass

print("\nSummary (Service 33 Packets):", counts)
sock.close()
