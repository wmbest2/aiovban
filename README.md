# VBAN Protocol Wrapper

[![Currently Under Development - WIP](https://img.shields.io/badge/Currently_Under_Development-WIP-yellow)](https://)

## Overview

This project aims to create a modern, ergonomic wrapper around the VBAN protocol. By leveraging modern Python tools such as dataclasses and asyncio, this wrapper provides a simple and efficient interface for working with VBAN.

## Features

- **Dataclasses**: Utilizes Python's dataclasses for clean, concise and ergonomic data structures.
- **Asyncio**: Supports asynchronous operations for non-blocking I/O.
- **Ease of Use**: Designed to be simple and intuitive, making it easy to integrate VBAN into your projects.

## Installation

To install the package, use pip:

```sh
pip install aiovban
```

## Usage

### Basic Example

Here's a basic example of how to use the VBAN wrapper:

```python
from aiovban import VBANAudioHeader, VBANPacket
from aiovban import VBANSampleRate

# Create a VBAN audio header
audio_header = VBANAudioHeader(sample_rate=VBANSampleRate.RATE_44100, channels=17, samples_per_frame=3,
                               bit_resolution=3, codec=0xf0, streamname="Channel1")

# Create a VBAN packet
packet = VBANPacket(header=audio_header)

# Access properties
print(packet.header.sample_rate)  # Output: 48000
print(packet.header.samples_per_frame)  # Output: 256
```

### Asynchronous Example

Using asyncio for non-blocking operations:

```python
client = AsyncVBANClient(ignore_audio_streams=False)
asyncio.create_task(client.listen('0.0.0.0', 6980)) # Listen for all incoming packets

windows_host = client.register_device('bill.local', 6980)
windows_mic_out = windows_host.receive_stream('Windows Mic Out')


command_stream = await windows_host.text_stream('Command1')
await command_stream.send_text('Strip[0].Gain = 0.5;')
await asyncio.sleep(1)
await command_stream.send_text('Command.Restart = 1;')

# DRAIN_OLDEST will dump half the queue when it becomes full
rt_stream = await windows_host.rt_stream(30, back_pressure_strategy=BackPressureStrategy.DRAIN_OLDEST)
print(await rt_stream.get_packet())


receiver = VBANAudioPlayer(stream=windows_mic_out)
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Contact

For any questions or issues, please open an issue on the GitHub repository.

---

This README provides a brief overview of the project, installation instructions, usage examples, and contribution guidelines.
