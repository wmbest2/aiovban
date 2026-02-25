import socket

def listen_vban():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 6980))
    print("Listening on 0.0.0.0:6980...")
    while True:
        data, addr = sock.recvfrom(2048)
        print(f"Received {len(data)} bytes from {addr}")
        if data.startswith(b"VBAN"):
            print(f"Raw hex: {data.hex()}")
            # Stop after first packet
            break

if __name__ == "__main__":
    listen_vban()
