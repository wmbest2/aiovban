# aiovban

An ergonomic, asyncio-first Python wrapper around the VBAN protocol.

[![PyPI version](https://img.shields.io/pypi/v/aiovban.svg)](https://pypi.org/project/aiovban/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

`aiovban` provides a modern interface for interacting with the VBAN protocol, commonly used with VoiceMeeter. It leverages Python's `asyncio` for high-performance, non-blocking I/O and `dataclasses` for clean, typed data structures.

## Features

- **Full Protocol Support**: VBAN Audio, Text (Command), Service (Ping/RT), and Serial.
- **Asyncio Native**: Built from the ground up for asynchronous applications with support for **uvloop**.
- **Performance Optimized**: 
  - **Zero-copy** data handling using `memoryview` to reduce memory allocations.
  - **Async Batch Draining** for high-throughput audio streams.
  - **Thread-safe** cross-thread packet delivery for stable real-time audio.
- **VoiceMeeter Abstraction**: High-level `VoicemeeterRemote` API for intuitive control of strips, buses, and engine commands.
- **Interactive TUI**: Includes `aiovban-tui`, a full-featured terminal mixer for remote VoiceMeeter control.
- **Audio Streaming**: Official support for PyAudio via the `aiovban-pyaudio` package.
- **Type Safety**: Extensively typed using Python dataclasses and enums.

## Installation

```sh
# Core library
pip install aiovban

# Audio streaming support (includes cli tools)
pip install aiovban-pyaudio[cli]
```

## Performance

For the best performance on macOS and Linux, ensure `uvloop` is installed. The CLI tools will automatically detect and use it to reduce CPU overhead:

```sh
pip install uvloop
```

`aiovban` uses "Zero-Copy" patterns throughout its audio pipeline. By using `memoryview` and synchronous fast-paths for packet handoff, the library minimizes the work the Python interpreter has to do, allowing for stable 48kHz+ audio streaming with low latency.

## Audio Streaming (aiovban-pyaudio)

The `aiovban-pyaudio` package provides a high-performance bridge between VBAN and your local sound card.

### Receiving Audio
```sh
aiovban-receiver 192.168.1.50/Stream1 --output-device "MacBook Pro Speakers"
```

### Sending Audio
```sh
aiovban-sender --address 192.168.1.50 --stream-name "MacMic" --input-device "Built-in Microphone"
```

## Usage

### High-Level VoiceMeeter Control (Recommended)

The `VoicemeeterRemote` class provides the easiest way to control a remote VoiceMeeter instance.

#### State Synchronization and Latency

It is important to understand how `VoicemeeterRemote` tracks the state of the remote mixer:

- **Unidirectional State**: The `VoicemeeterRemote` object only reflects the state received from VoiceMeeter via **RT (Real-Time) packets**. It does not optimistically update its local state when you call a `set_` method.
- **Update Latency**: When you call a method like `strip.set_mute(True)`, a VBAN-TEXT command is sent to VoiceMeeter. The value of `strip.mute` will **not** change until VoiceMeeter processes the command and sends back a new RT packet reflecting the change.
- **Poll-based**: By default, `VoicemeeterRemote` registers for RT packets at a specific interval. The delay between setting a value and seeing it update in the API is typically between 20ms and 500ms, depending on network conditions and the `update_interval` configured.

```python
import asyncio
from aiovban.asyncio import AsyncVBANClient, VoicemeeterRemote

async def main():
    client = AsyncVBANClient()
    await client.listen("0.0.0.0", 6980)

    # Register a remote VoiceMeeter device
    device = await client.register_device("192.168.1.50")
    
    # Initialize the high-level remote
    vm = VoicemeeterRemote(device)

    # Toggle mute on the first strip
    await vm.strips[0].set_mute(True)
    
    # Set gain on the first bus
    await vm.buses[0].set_gain(-10.5)
    
    # Restart the audio engine
    await vm.restart()

asyncio.run(main())
```

### Low-Level Protocol Usage

For applications requiring direct stream access, you can interact with the client and streams directly.

#### Sending Commands via Text Streams
```python
# Create a text stream for outgoing commands
command_stream = await device.text_stream('Command1')
await command_stream.send_text('Strip[0].Mute = 1;')
```

#### Receiving RT Packets (Real-time State)
```python
from aiovban.asyncio.util import BackPressureStrategy

# Subscribe to RT updates (30 times per second)
rt_stream = await device.rt_stream(30, back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST)

# Get the next incoming packet
packet = await rt_stream.get_packet()
print(f"Master Gain: {packet.body.buses[0].gain}")
```

#### Manual Packet Construction
```python
from aiovban.packet import VBANPacket
from aiovban.packet.headers.audio import VBANAudioHeader
from aiovban.enums import VBANSampleRate

# Construct a custom VBAN audio header
header = VBANAudioHeader(
    sample_rate=VBANSampleRate.RATE_44100, 
    channels=2, 
    samples_per_frame=256,
    streamname="Stream1"
)

# Wrap in a packet
packet = VBANPacket(header=header, body=b'\x00' * 1024)
packed_bytes = packet.pack()
```

### Interactive TUI

`aiovban` comes with a powerful terminal-based mixer. You can launch it directly from your terminal:

```sh
aiovban-tui --register 192.168.1.50
```

*Note: Click on strip titles to rename them.*

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details on our development workflow and coding standards.
