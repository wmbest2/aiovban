import asyncio
import subprocess
import time

async def run_test():
    print("Starting receiver...")
    # Run receiver in background
    # Note: Using python -m or the installed script name
    receiver = subprocess.Popen([
        "uv", "run", "aiovban-receiver", 
        "--debug",
        "--host-address", "127.0.0.1",
        "--host-port", "6980",
        "--output-device", "MacBook Pro Speakers",
        "--channels", "1",
        "--sample-rate", "44100",
        "127.0.0.1:6980/TestStream"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    await asyncio.sleep(2)  # Give receiver time to start

    print("Starting sender...")
    sender = subprocess.Popen([
        "uv", "run", "aiovban-sender",
        "--debug",
        "--address", "127.0.0.1",
        "--port", "6980",
        "--input-device", "MacBook Pro Microphone",
        "--stream-name", "TestStream",
        "--channels", "1",
        "--sample-rate", "44100"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    print("Running for 5 seconds...")
    await asyncio.sleep(5)

    print("Stopping sender and receiver...")
    sender.terminate()
    receiver.terminate()
    
    sender_out, _ = sender.communicate()
    receiver_out, _ = receiver.communicate()

    print("\n--- Receiver Output ---")
    print(receiver_out)
    print("\n--- Sender Output ---")
    print(sender_out)
    print("Test complete.")

if __name__ == "__main__":
    asyncio.run(run_test())
