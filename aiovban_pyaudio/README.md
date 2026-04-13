# aiovban-pyaudio

A high-performance PyAudio bridge for the `aiovban` ecosystem.

## Overview

`aiovban-pyaudio` provides the necessary tools and libraries to bridge VBAN network audio with your local sound hardware. It is built on top of `aiovban` and leverages its zero-copy architecture for stable, high-bitrate audio streaming with minimal CPU overhead.

## Features

- **High-Performance Bridge**: Leverages `memoryview` and zero-copy patterns for efficient audio transfer.
- **Asynchronous Loop Support**: Full support for `uvloop` for low-latency network handling.
- **Command-Line Tools**: Ready-to-use binaries for receiving and sending audio.
- **Dynamic Resampling**: Handles stream format changes (channels, sample rate) in real-time.

## Installation

```sh
pip install aiovban-pyaudio[cli]
```

## CLI Usage

### Receiving Audio
Connect to a remote VBAN stream and play it through your local speakers:

```sh
# aiovban-receiver <host>/<stream_name>
aiovban-receiver 192.168.1.50/Stream1 --output-device "Speakers"
```

### Sending Audio
Capture audio from your local microphone and send it over the network:

```sh
aiovban-sender --address 192.168.1.50 --stream-name "Mic" --input-device "Microphone"
```

## Advanced Usage

You can use the `VBANAudioPlayer` and `VBANAudioSender` classes directly in your own `asyncio` applications for deep integration.

```python
from aiovban_pyaudio import VBANAudioPlayer
from aiovban.asyncio import AsyncVBANClient

# ... register device and get stream ...
player = VBANAudioPlayer(stream=stream)
await player.listen()
```

## License

This project is licensed under the MIT License.
