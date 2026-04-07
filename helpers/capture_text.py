import asyncio
import logging
import signal
from aiovban.asyncio import AsyncVBANClient
from aiovban.packet.headers.text import VBANTextHeader
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType, PingFunctions
from aiovban.packet.body import Utf8StringBody

# Configure logging to show information level messages
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class TextCaptureClient(AsyncVBANClient):
    """
    A VBAN client that overrides quick_reject to accept packets from any source
    and logs VBAN text and chat commands.
    """
    def quick_reject(self, address):
        # We want to capture packets from any source, so we never reject.
        return False

    async def process_packet(self, address, port, packet):
        # Handle regular VBAN Text packets
        if isinstance(packet.header, VBANTextHeader):
            stream_name = packet.header.streamname
            if isinstance(packet.body, Utf8StringBody):
                print(f"[{address}:{port}] TEXT '{stream_name}': {packet.body.text}")
            else:
                print(f"[{address}:{port}] TEXT '{stream_name}': (body type {type(packet.body)})")
        
        # Handle VBAN Service packets
        elif isinstance(packet.header, VBANServiceHeader):
            if packet.header.service == ServiceType.Chat_UTF8:
                if isinstance(packet.body, Utf8StringBody):
                    print(f"[{address}:{port}] CHAT: {packet.body.text}")
                else:
                    print(f"[{address}:{port}] CHAT: (body type {type(packet.body)})")
            
            elif packet.header.service == ServiceType.Identification:
                if packet.header.function == PingFunctions.Request:
                    print(f"[{address}:{port}] PING REQ: Responding...")
                    # AsyncVBANClient.process_packet already handles responding, 
                    # but we'll call it via super() or just do it here for clarity.
                elif packet.header.function == PingFunctions.Response:
                    print(f"[{address}:{port}] PING RES: {packet.body}")
        
        # Call super to handle other packets (like Pings) normally
        await super().process_packet(address, port, packet)

import argparse

async def main():
    parser = argparse.ArgumentParser(description="VBAN Text Capture Helper")
    parser.add_argument("--port", type=int, default=6980, help="Port to listen on (default: 6980)")
    parser.add_argument("--address", default="0.0.0.0", help="Address to listen on (default: 0.0.0.0)")
    args = parser.parse_args()

    client = TextCaptureClient()
    
    print(f"Starting VBAN Text Capture on {args.address}:{args.port}...")
    print("Press Ctrl+C to stop.")
    
    try:
        # Start listening
        await client.listen(address=args.address, port=args.port)
        
        # Keep the script running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        client.close()
        print("\nStopped VBAN Text Capture.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
