from dataclasses import dataclass, field
import struct

from .. import PacketBody
from ....enums import VBANSampleRate, State, VoicemeeterType


@dataclass
class Bus:
    label: str
    state: State
    gain: int


@dataclass
class Strip:
    label: str
    state: State
    layers: list = field(repr=False)


@dataclass
class RTPacketBodyType0(PacketBody):
    voice_meeter_type: VoicemeeterType
    buffer_size: int
    voice_meeter_version: str
    sample_rate: VBANSampleRate
    input_levels: list = field(repr=False)
    output_levels: list = field(repr=False)
    transport_bits: int = field(repr=False)
    strips: list
    buses: list

    @classmethod
    def versionFromBytes(cls, data):
        return f"{data[4]}.{data[5]}.{data[6]}.{data[7]}"

    @classmethod
    def buildBuses(cls, data):
        # Validate data size for bus operations
        if len(data) < 1384:  # Minimum size needed for 8 buses (904 + 8*60)
            raise ValueError(f"Insufficient data for bus parsing: expected at least 1384 bytes, got {len(data)}")
        
        try:
            bus_states = struct.unpack("<" + "L" * 8, data[248:280])
            bus_gain = struct.unpack("<" + "H" * 8, data[408:424])
        except struct.error as e:
            raise ValueError(f"Failed to unpack bus data: {e}")

        bus_names = []
        for n in range(8):
            bus_start = 904 + (n * 60)
            bus_end = bus_start + 60
            if bus_end > len(data):
                raise ValueError(f"Insufficient data for bus {n}: data ends at {len(data)}, need {bus_end}")
            try:
                bus_names.append(
                    data[bus_start:bus_end].decode("utf-8", errors="ignore").strip("\x00")
                )
            except UnicodeDecodeError:
                bus_names.append("")  # Fallback for invalid UTF-8

        return [
            Bus(label=bus_names[n], state=State(bus_states[n]), gain=bus_gain[n])
            for n in range(8)
        ]

    @classmethod
    def buildStrips(cls, data):
        # Validate data size for strip operations
        if len(data) < 904:  # Minimum size needed for strips (424 + 8*60)
            raise ValueError(f"Insufficient data for strip parsing: expected at least 904 bytes, got {len(data)}")

        try:
            strip_states = struct.unpack("<" + "L" * 8, data[216:248])
            layer1_gain = struct.unpack("<" + "H" * 8, data[280:296])
            layer2_gain = struct.unpack("<" + "H" * 8, data[296:312])
            layer3_gain = struct.unpack("<" + "H" * 8, data[312:328])
            layer4_gain = struct.unpack("<" + "H" * 8, data[328:344])
            layer5_gain = struct.unpack("<" + "H" * 8, data[344:360])
            layer6_gain = struct.unpack("<" + "H" * 8, data[360:376])
            layer7_gain = struct.unpack("<" + "H" * 8, data[376:392])
            layer8_gain = struct.unpack("<" + "H" * 8, data[392:408])
        except struct.error as e:
            raise ValueError(f"Failed to unpack strip data: {e}")

        strip_names = []
        for n in range(8):
            strip_start = 424 + (n * 60)
            strip_end = strip_start + 60
            if strip_end > len(data):
                raise ValueError(f"Insufficient data for strip {n}: data ends at {len(data)}, need {strip_end}")
            try:
                strip_names.append(
                    data[strip_start:strip_end].decode("utf-8", errors="ignore").strip("\x00")
                )
            except UnicodeDecodeError:
                strip_names.append("")  # Fallback for invalid UTF-8

        strips = []
        for n in range(8):
            strip = Strip(
                label=strip_names[n],
                state=State(strip_states[n]),
                layers=[
                    layer1_gain[n],
                    layer2_gain[n],
                    layer3_gain[n],
                    layer4_gain[n],
                    layer5_gain[n],
                    layer6_gain[n],
                    layer7_gain[n],
                    layer8_gain[n],
                ],
            )
            strips.append(strip)
        return strips

    @classmethod
    def unpack(cls, data):
        # Validate minimum data size
        if len(data) < 1384:  # Minimum size for complete RT packet
            raise ValueError(f"Insufficient data for RT packet: expected at least 1384 bytes, got {len(data)}")
        
        try:
            print(data)
            return RTPacketBodyType0(
                voice_meeter_type=VoicemeeterType(data[0]),
                # reserved = data[1],
                buffer_size=struct.unpack("<H", data[2:4])[0],
                voice_meeter_version=cls.versionFromBytes(data),
                # optionBits = data[8:12]
                sample_rate=VBANSampleRate(struct.unpack("<L", data[12:16])[0]),
                input_levels=list(struct.unpack("<" + "H" * 34, data[16:84])),
                output_levels=list(struct.unpack("<" + "H" * 64, data[84:212])),
                transport_bits=struct.unpack("<L", data[212:216])[0],
                strips=cls.buildStrips(data),
                buses=cls.buildBuses(data),
            )
        except (struct.error, ValueError) as e:
            raise ValueError(f"Failed to unpack RT packet: {e}")

    def pack(self):
        version_bytes = struct.pack(
            "<BBBB", *[int(v) for v in self.voice_meeter_version.split(".")]
        )
        input_levels_bytes = struct.pack("<" + "H" * 34, *self.input_levels)
        output_levels_bytes = struct.pack("<" + "H" * 64, *self.output_levels)
        transport_bits_bytes = struct.pack("<L", self.transport_bits)

        strip_states_bytes = struct.pack(
            "<" + "L" * 8, *[int(strip.state) for strip in self.strips]
        )
        layer_gains_bytes = b"".join(
            struct.pack("<" + "H" * 8, *[strip.layers[i] for strip in self.strips])
            for i in range(8)
        )
        print(len(layer_gains_bytes))
        bus_states_bytes = struct.pack(
            "<" + "L" * 8, *[int(bus.state) for bus in self.buses]
        )
        bus_gains_bytes = struct.pack("<" + "H" * 8, *[bus.gain for bus in self.buses])
        strip_names_bytes = b"".join(
            struct.pack("<60s", strip.label.encode("utf-8")) for strip in self.strips
        )
        bus_names_bytes = b"".join(
            struct.pack("<60s", bus.label.encode("utf-8")) for bus in self.buses
        )

        return (
            struct.pack("<B", self.voice_meeter_type.value)
            + b"\x00"  # reserved
            + struct.pack("<H", self.buffer_size)
            + version_bytes
            + b"\x00" * 4  # optionBits
            + struct.pack("<L", self.sample_rate.value)
            + input_levels_bytes
            + output_levels_bytes
            + transport_bits_bytes
            + strip_states_bytes
            + bus_states_bytes
            + layer_gains_bytes
            + bus_gains_bytes
            + strip_names_bytes
            + bus_names_bytes
        )
