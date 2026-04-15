from dataclasses import dataclass, field
import struct

from .. import PacketBody
from ....enums import VBANSampleRate, State, VoicemeeterType

# Minimum packet size for RT packets: 28 byte header + 1356 byte body
# Body structure: 1 (type) + 1 (reserved) + 2 (buffer) + 4 (version) + 4 (options) +
#                 4 (rate) + 68 (input levels) + 128 (output levels) + 4 (transport) +
#                 32 (strip states) + 32 (bus states) + 128 (layers) + 16 (bus gain) +
#                 480 (strip names) + 480 (bus names) = 1384 bytes minimum
MIN_RT_PACKET_SIZE = 1384


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
        if len(data) < MIN_RT_PACKET_SIZE:
            raise ValueError(
                f"Insufficient data for bus parsing: expected at least {MIN_RT_PACKET_SIZE} bytes, got {len(data)}"
            )

        try:
            bus_states = struct.unpack("<" + "L" * 8, data[248:280])
            bus_gain = struct.unpack("<" + "h" * 8, data[408:424])
        except struct.error as e:
            raise ValueError(f"Failed to unpack bus data: {e}")

        bus_names = []
        for n in range(8):
            bus_start = 904 + (n * 60)
            bus_end = bus_start + 60
            if bus_end > len(data):
                raise ValueError(
                    f"Insufficient data for bus {n}: data ends at {len(data)}, need {bus_end}"
                )
            # memoryview doesn't have decode, so we convert to bytes
            chunk = data[bus_start:bus_end]
            if isinstance(chunk, memoryview):
                chunk = chunk.tobytes()
            bus_names.append(chunk.decode("utf-8").strip("\x00"))

        return [
            Bus(label=bus_names[n], state=State(bus_states[n]), gain=bus_gain[n])
            for n in range(8)
        ]

    @classmethod
    def buildStrips(cls, data):
        # Validate data size for strip operations
        if len(data) < 904:  # Minimum size needed for strips (424 + 8*60)
            raise ValueError(
                f"Insufficient data for strip parsing: expected at least 904 bytes, got {len(data)}"
            )

        try:
            strip_states = struct.unpack("<" + "L" * 8, data[216:248])
            layer1_gain = struct.unpack("<" + "h" * 8, data[280:296])
            layer2_gain = struct.unpack("<" + "h" * 8, data[296:312])
            layer3_gain = struct.unpack("<" + "h" * 8, data[312:328])
            layer4_gain = struct.unpack("<" + "h" * 8, data[328:344])
            layer5_gain = struct.unpack("<" + "h" * 8, data[344:360])
            layer6_gain = struct.unpack("<" + "h" * 8, data[360:376])
            layer7_gain = struct.unpack("<" + "h" * 8, data[376:392])
            layer8_gain = struct.unpack("<" + "h" * 8, data[392:408])
        except struct.error as e:
            raise ValueError(f"Failed to unpack strip data: {e}")

        strip_names = []
        for n in range(8):
            strip_start = 424 + (n * 60)
            strip_end = strip_start + 60
            if strip_end > len(data):
                raise ValueError(
                    f"Insufficient data for strip {n}: data ends at {len(data)}, need {strip_end}"
                )
            # memoryview doesn't have decode, so we convert to bytes
            chunk = data[strip_start:strip_end]
            if isinstance(chunk, memoryview):
                chunk = chunk.tobytes()
            strip_names.append(chunk.decode("utf-8").strip("\x00"))

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
        if len(data) < MIN_RT_PACKET_SIZE:
            raise ValueError(
                f"Insufficient data for RT packet: expected at least {MIN_RT_PACKET_SIZE} bytes, got {len(data)}"
            )

        try:
            return RTPacketBodyType0(
                voice_meeter_type=VoicemeeterType(data[0]),
                # reserved = data[1],
                buffer_size=struct.unpack("<H", data[2:4])[0],
                voice_meeter_version=cls.versionFromBytes(data),
                # optionBits = data[8:12]
                sample_rate=VBANSampleRate.find(struct.unpack("<L", data[12:16])[0]),
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
            struct.pack("<" + "h" * 8, *[strip.layers[i] for strip in self.strips])
            for i in range(8)
        )
        bus_states_bytes = struct.pack(
            "<" + "L" * 8, *[int(bus.state) for bus in self.buses]
        )
        bus_gains_bytes = struct.pack("<" + "h" * 8, *[bus.gain for bus in self.buses])
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
            + struct.pack("<L", self.sample_rate.rate)
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

@dataclass
class StripParam:
    mode: int
    dblevel: float
    audibility: int
    pos3d: tuple[int, int]
    poscolor: tuple[int, int]
    eqgain: list[int]
    peq_on: list[int]
    peq_type: list[int]
    peq_gain: list[float]
    peq_freq: list[float]
    peq_q: list[float]
    audibility_c: int
    audibility_g: int
    audibility_d: int
    posmod: tuple[int, int]
    send: list[int]
    dblimit: int
    nkaraoke: int
    comp: dict
    gate: dict
    denoiser: int
    pitch: dict


@dataclass
class RTPacketBodyType1(PacketBody):
    voice_meeter_type: VoicemeeterType
    buffer_size: int
    voice_meeter_version: str
    sample_rate: VBANSampleRate
    transport_bits: int
    strips: list[StripParam]

    @classmethod
    def versionFromBytes(cls, data):
        return f"{data[4]}.{data[5]}.{data[6]}.{data[7]}"

    @classmethod
    def unpack(cls, data):
        try:
            strips = []
            for n in range(8):
                offset = 16 + (n * 174)
                s_data = data[offset : offset + 174]
                
                # Unpack the fixed part (24 bytes)
                fixed = struct.unpack("<Lfhhhhhhhh", s_data[0:24])
                
                # Unpack PEQ part (84 bytes)
                peq_on = list(struct.unpack("<BBBBBB", s_data[24:30]))
                peq_type = list(struct.unpack("<BBBBBB", s_data[30:36]))
                peq_gain = list(struct.unpack("<ffffff", s_data[36:60]))
                peq_freq = list(struct.unpack("<ffffff", s_data[60:84]))
                peq_q = list(struct.unpack("<ffffff", s_data[84:108]))
                
                # Unpack the rest (66 bytes)
                # 108: 11 shorts (22 bytes) -> 130
                # 130: Compressor (9 shorts, 18 bytes) -> 148
                # 148: Gate (6 shorts, 12 bytes) -> 160
                # 160: Denoiser (1 short, 2 bytes) -> 162
                # 162: Pitch (6 shorts, 12 bytes) -> 174
                rest = struct.unpack("<hhhhhhhhhhh hhhhhhhhh hhhhhh h hhhhhh", s_data[108:174])
                
                strip = StripParam(
                    mode=fixed[0],
                    dblevel=fixed[1],
                    audibility=fixed[2],
                    pos3d=(fixed[3], fixed[4]),
                    poscolor=(fixed[5], fixed[6]),
                    eqgain=[fixed[7], fixed[8], fixed[9]],
                    peq_on=peq_on,
                    peq_type=peq_type,
                    peq_gain=peq_gain,
                    peq_freq=peq_freq,
                    peq_q=peq_q,
                    audibility_c=rest[0],
                    audibility_g=rest[1],
                    audibility_d=rest[2],
                    posmod=(rest[3], rest[4]),
                    send=[rest[5], rest[6], rest[7], rest[8]],
                    dblimit=rest[9],
                    nkaraoke=rest[10],
                    comp={
                        "gain_in": rest[11],
                        "attack": rest[12],
                        "release": rest[13],
                        "knee": rest[14],
                        "ratio": rest[15],
                        "threshold": rest[16],
                        "enabled": rest[17],
                        "auto": rest[18],
                        "gain_out": rest[19],
                    },
                    gate={
                        "threshold": rest[20],
                        "damping": rest[21],
                        "sidechain": rest[22],
                        "attack": rest[23],
                        "hold": rest[24],
                        "release": rest[25],
                    },
                    denoiser=rest[26],
                    pitch={
                        "enabled": rest[27],
                        "drywet": rest[28],
                        "value": rest[29],
                        "lo": rest[30],
                        "med": rest[31],
                        "high": rest[32],
                    }
                )
                strips.append(strip)

            return RTPacketBodyType1(
                voice_meeter_type=VoicemeeterType(data[0]),
                buffer_size=struct.unpack("<H", data[2:4])[0],
                voice_meeter_version=cls.versionFromBytes(data),
                sample_rate=VBANSampleRate.find(struct.unpack("<L", data[12:16])[0]),
                transport_bits=data[8],
                strips=strips
            )
        except (struct.error, ValueError) as e:
            raise ValueError(f"Failed to unpack RT packet type 1: {e}")

    def pack(self):
        # Implementation of pack for Type 1 if needed
        raise NotImplementedError("Packing Type 1 RT packets is not implemented")
