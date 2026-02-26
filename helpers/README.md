# Helper Scripts

This directory contains utility scripts for testing and debugging the `aiovban` workspace.

## Scripts

### `list_devices.py`
Lists all available PyAudio devices on the current system. Use this to find the correct device names or indices for the sender and receiver.

**Usage:**
```bash
uv run python helpers/list_devices.py
```

### `e2e_test.py`
Performs an end-to-end test by spawning an `aiovban-receiver` and an `aiovban-sender` as subprocesses. It transmits audio from the default microphone to the default speakers via VBAN over localhost for 5 seconds.

**Usage:**
```bash
uv run python helpers/e2e_test.py
```

> **Note:** You may need to edit the script to match your specific hardware device names (e.g., "MacBook Pro Microphone") if the defaults fail.
