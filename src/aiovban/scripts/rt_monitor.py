import argparse
import asyncio
import json
import struct
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient
from aiovban.enums import Features, State
from aiovban.packet import VBANPacket
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType
from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0


@dataclass
class ChannelStatus:
    name: str
    address: str
    last_seen: float
    channels: int
    sample_rate: int
    bit_depth: int
    levels: List[float] = field(default_factory=list)
    type: str = "audio"
    mute: bool = False
    solo: bool = False
    gain: float = 0.0


class Monitor:
    def __init__(self, output_format="text", timeout=5.0):
        self.output_format = output_format
        self.timeout = timeout
        self.channels: Dict[str, ChannelStatus] = {}
        self.packets_received = 0
        self.rt_packets_received = 0
        self.start_time = time.time()

    def calculate_levels(self, data: bytes, bit_res: BitResolution, channels: int) -> List[float]:
        if not data:
            return [0.0] * channels

        try:
            if bit_res == BitResolution.INT16:
                fmt = f"<{len(data)//2}h"
                samples = struct.unpack(fmt, data)
                max_val = 32768
            elif bit_res == BitResolution.BYTE8:
                fmt = f"<{len(data)}B"
                samples = [s - 128 for s in struct.unpack(fmt, data)]
                max_val = 128
            elif bit_res == BitResolution.INT32 or bit_res == BitResolution.FLOAT32:
                fmt = f"<{len(data)//4}f" if bit_res == BitResolution.FLOAT32 else f"<{len(data)//4}i"
                samples = struct.unpack(fmt, data)
                max_val = 1.0 if bit_res == BitResolution.FLOAT32 else 2147483648
            else:
                return [0.0] * channels
        except Exception:
            return [0.0] * channels

        levels = [0.0] * channels
        if not samples:
            return levels

        for i, sample in enumerate(samples):
            ch = i % channels
            levels[ch] = max(levels[ch], abs(sample) / max_val)
        return levels

    def process_packet(self, address: str, packet: VBANPacket):
        now = time.time()
        self.packets_received += 1
        header = packet.header

        if isinstance(header, VBANAudioHeader):
            stream_key = f"{address}/{header.streamname}"
            levels = self.calculate_levels(packet.body.pack(), header.bit_resolution, header.channels)
            self.channels[stream_key] = ChannelStatus(
                name=header.streamname,
                address=address,
                last_seen=now,
                channels=header.channels,
                sample_rate=header.sample_rate.rate,
                bit_depth=header.bit_resolution.byte_width * 8,
                levels=levels,
                type="audio",
            )

        elif isinstance(header, VBANServiceHeader):
            if header.service == ServiceType.RTPacket and isinstance(packet.body, RTPacketBodyType0):
                self.rt_packets_received += 1
                body: RTPacketBodyType0 = packet.body

                for i, strip in enumerate(body.strips):
                    name = strip.label or f"Strip {i + 1}"
                    strip_key = f"{address}/strip/{i}"
                    if i < 5:
                        levels_raw = body.input_levels[i * 2 : (i + 1) * 2]
                    else:
                        levels_raw = body.input_levels[10 + (i - 5) * 8 : 10 + (i - 4) * 8]
                    levels = [lv / 65535.0 for lv in levels_raw]
                    self.channels[strip_key] = ChannelStatus(
                        name=name,
                        address=address,
                        last_seen=now,
                        channels=len(levels),
                        sample_rate=body.sample_rate.rate,
                        bit_depth=16,
                        levels=levels,
                        type="strip",
                        mute=bool(strip.state & State.MODE_MUTE),
                        solo=bool(strip.state & State.MODE_SOLO),
                    )

                for i, bus in enumerate(body.buses):
                    name = bus.label or f"Bus {i + 1}"
                    bus_key = f"{address}/bus/{i}"
                    levels_raw = body.output_levels[i * 8 : (i + 1) * 8]
                    levels = [lv / 65535.0 for lv in levels_raw]
                    self.channels[bus_key] = ChannelStatus(
                        name=name,
                        address=address,
                        last_seen=now,
                        channels=len(levels),
                        sample_rate=body.sample_rate.rate,
                        bit_depth=16,
                        levels=levels,
                        type="bus",
                        mute=bool(bus.state & State.MODE_MUTE),
                        gain=float(bus.gain),
                    )

    def cleanup(self):
        now = time.time()
        self.channels = {k: v for k, v in self.channels.items() if now - v.last_seen < self.timeout}

    def display(self, raw_packets=0):
        self.cleanup()
        elapsed = time.time() - self.start_time

        print("\033[H\033[J", end="")
        print(f"VBAN Monitor  —  uptime {elapsed:.0f}s  |  raw UDP: {raw_packets}  |  parsed: {self.packets_received}  |  RT: {self.rt_packets_received}")
        print("-" * 80)

        if not self.channels:
            print("  Waiting for VBAN data...")
            print("  (check VBAN is enabled in VoiceMeeter and the host IP is correct)")
            return

        print(f"{'Type':<8} {'Name':<20} {'Address':<18} {'Levels'}")
        print("-" * 80)

        strips = {k: v for k, v in self.channels.items() if v.type == "strip"}
        buses  = {k: v for k, v in self.channels.items() if v.type == "bus"}
        audio  = {k: v for k, v in self.channels.items() if v.type == "audio"}

        for section_label, section in [("Strips", strips), ("Buses", buses), ("Audio", audio)]:
            if not section:
                continue
            print(f"  {section_label}")
            for v in section.values():
                bar = ""
                for lv in v.levels[:4]:
                    filled = int(lv * 10)
                    bar += f"[{'█' * filled}{' ' * (10 - filled)}] "
                status = ""
                if v.mute:
                    status += " [MUTE]"
                if v.solo:
                    status += " [SOLO]"
                print(f"  {v.type:<6} {v.name[:20]:<20} {v.address:<18} {bar}{status}")


async def run_monitor(args):
    application_data = VBANApplicationData(
        application_name="VBAN Monitor",
        features=Features.Text | Features.Audio,
        device_type=DeviceType.Receptor,
        version="0.1.0",
    )

    client = AsyncVBANClient(ignore_audio_streams=False, application_data=application_data)
    client.quick_reject = lambda addr: False

    monitor = Monitor(output_format=args.format, timeout=args.timeout)

    original_process_packet = client.process_packet

    async def hooked_process_packet(address, port, packet):
        monitor.process_packet(address, packet)
        await original_process_packet(address, port, packet)

    client.process_packet = hooked_process_packet

    await client.listen(args.host, args.port)
    print(f"Listening on {args.host}:{args.port}...")

    if args.register:
        for addr in args.register:
            host, *port_parts = addr.split(":")
            port = int(port_parts[0]) if port_parts else 6980
            device = await client.register_device(host, port)
            await device.rt_stream(update_interval=args.interval)
            print(f"Registered for RT updates from {host}:{port}")

    try:
        while True:
            if args.format == "text":
                monitor.display(raw_packets=client.raw_packets_received)
            elif args.format == "json":
                output = {k: asdict(v) for k, v in monitor.channels.items()}
                print(json.dumps(output))
            await asyncio.sleep(args.refresh)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="VBAN Real-time Monitor")
    parser.add_argument("--host", default="0.0.0.0", help="Address to listen on")
    parser.add_argument("--port", type=int, default=6980, help="Port to listen on")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--refresh", type=float, default=0.1, help="Refresh interval in seconds")
    parser.add_argument("--timeout", type=float, default=5.0, help="Stream timeout in seconds")
    parser.add_argument("--interval", type=int, default=0xFF, help="RT update interval (0-255)")
    parser.add_argument("--register", nargs="+", help="Devices to register for RT updates (address[:port])")

    args = parser.parse_args()
    asyncio.run(run_monitor(args))


if __name__ == "__main__":
    main()
