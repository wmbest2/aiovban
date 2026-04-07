"""
Minimal UDP test — no asyncio, no library code.
Run this, then check if VoiceMeeter sends anything.
"""
import socket
import struct
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 6980
REGISTER_HOST = sys.argv[2] if len(sys.argv) > 2 else None

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
sock.bind(("0.0.0.0", PORT))
sock.settimeout(10)

print(f"Listening on 0.0.0.0:{PORT}")

if REGISTER_HOST:
    # Send a raw VBAN RTPacketRegister to VoiceMeeter
    # Header: "VBAN" + subprotocol(SERVICE=0x60) + byte_a(0) + service(0x20) + interval(0xFF)
    #         + streamname(16 bytes) + framecount(4 bytes)
    streamname = b"Command1\x00\x00\x00\x00\x00\x00\x00\x00"
    header = b"VBAN" + bytes([0x60, 0x00, 0x20, 0xFF]) + streamname + struct.pack("<L", 0)
    reg_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reg_sock.sendto(header, (REGISTER_HOST, 6980))
    reg_sock.close()
    print(f"Sent RTPacketRegister to {REGISTER_HOST}:6980")

print("Waiting for packets (10s timeout)...")
try:
    while True:
        data, addr = sock.recvfrom(4096)
        magic = data[:4]
        print(f"Got {len(data)} bytes from {addr}  magic={magic}")
except socket.timeout:
    print("No packets received in 10 seconds.")
finally:
    sock.close()
