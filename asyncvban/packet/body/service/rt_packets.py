from dataclasses import dataclass, field
import struct

from asyncvban.enums import VBANSampleRate, State, VoicemeeterType


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
class RTPacketBodyType0:
    voiceMeeterType: VoicemeeterType
    buffersize: int
    voiceMeeterVersion: str
    samplerate: VBANSampleRate
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
        bus_states = struct.unpack("<" + "L"*8, data[248:280])
        bus_gain = struct.unpack("<" + "H"*8, data[404:420])

        bus_names = []
        for n in range(8):
            bus_start = 900 + (n * 60)
            bus_names.append(data[bus_start:bus_start+60].decode("utf-8").strip("\x00"))

        return [Bus(label=bus_names[n], state=State(bus_states[n]), gain=bus_gain[n]) for n in range(8)]

    @classmethod
    def buildStrips(cls, data):

        strip_states = struct.unpack("<" + "L"*8, data[216:248])
        print(strip_states[0])
        layer1_gain = struct.unpack("<" + "H"*8, data[280:296])
        layer2_gain = struct.unpack("<" + "H"*8, data[296:312])
        layer3_gain = struct.unpack("<" + "H"*8, data[312:328])
        layer4_gain = struct.unpack("<" + "H"*8, data[328:344])
        layer5_gain = struct.unpack("<" + "H"*8, data[344:360])
        layer6_gain = struct.unpack("<" + "H"*8, data[360:376])
        layer7_gain = struct.unpack("<" + "H"*8, data[376:392])
        layer8_gain = struct.unpack("<" + "H"*8, data[392:408])

        strip_names = []
        for n in range(8):
            strip_start = 420 + (n * 60)
            strip_names.append(data[strip_start:strip_start+60].decode("utf-8").strip("\x00"))

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
                ]
            )
            strips.append(strip)
        return strips

    @classmethod
    def unpack(cls, data):
        return RTPacketBodyType0(
            voiceMeeterType = VoicemeeterType(data[0]),
            # reserved = data[1],
            buffersize = struct.unpack("<H", data[2:4])[0],
            voiceMeeterVersion = cls.versionFromBytes(data),
            # optionBits = data[8:12]
            samplerate = VBANSampleRate.find(struct.unpack("<L", data[12:16])[0]),
            input_levels = list(struct.unpack("<" + "H"*34, data[16:84])),
            output_levels=list(struct.unpack("<" + "H" * 64, data[84:212])),
            transport_bits=struct.unpack("<L", data[212:216])[0],
            strips=cls.buildStrips(data),
            buses=cls.buildBuses(data)
        )

