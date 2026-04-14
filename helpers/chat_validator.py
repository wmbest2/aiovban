import asyncio
import argparse
import logging
import sys
from aiovban.asyncio import AsyncVBANClient
from aiovban.asyncio.streams import VBANChatStream

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def run_listener(chat_stream: VBANChatStream):
    print(f"Listening for chat messages on stream '{chat_stream.name}'...")
    while True:
        try:
            message = await chat_stream.get_chat()
            print(f"\n[Received] {message}")
            print("> ", end="", flush=True)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error receiving chat: {e}")

async def run_sender(chat_stream: VBANChatStream):
    print(f"Chat Sender active on stream '{chat_stream.name}'.")
    print("Type your message and press Enter to send. Type 'exit' to quit.")
    
    loop = asyncio.get_running_loop()
    while True:
        # Use run_in_executor to avoid blocking the event loop with input()
        message = await loop.run_in_executor(None, lambda: input("> "))
        
        if message.lower() in ["exit", "quit"]:
            break
            
        if message:
            try:
                await chat_stream.send_chat(message)
                print(f"[Sent] {message}")
            except Exception as e:
                logger.error(f"Error sending chat: {e}")

async def main():
    parser = argparse.ArgumentParser(description="VBAN Chat Validation Utility")
    parser.add_argument("address", help="IP address of the remote VBAN device")
    parser.add_argument("--remote-port", type=int, default=6980, help="Remote VBAN port (default: 6980)")
    parser.add_argument("--local-port", type=int, default=0, help="Local port to bind to (default: 0, auto-assign)")
    parser.add_argument("--stream", default="VBAN Chat", help="Stream name (default: 'VBAN Chat')")
    parser.add_argument("--mode", choices=["both", "send", "listen"], default="both", 
                        help="Operating mode (default: both)")
    
    args = parser.parse_args()

    client = AsyncVBANClient()
    # We need to listen to receive messages
    await client.listen(address="0.0.0.0", port=args.local_port)
    
    # Get the actual port if we used 0
    local_addr = client._transport.get_extra_info("sockname")
    print(f"Local listener bound to {local_addr[0]}:{local_addr[1]}")
    
    try:
        device = await client.register_device(args.address, args.remote_port)
        chat = await device.chat_stream(args.stream)

        tasks = []
        if args.mode in ["both", "listen"]:
            tasks.append(asyncio.create_task(run_listener(chat)))
        
        if args.mode in ["both", "send"]:
            tasks.append(asyncio.create_task(run_sender(chat)))

        if tasks:
            await asyncio.gather(*tasks)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        client.close()
        print("\nUtility stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
