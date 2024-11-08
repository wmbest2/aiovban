from enum import Enum, Flag, auto


class VoicemeeterType(Enum):
    VOICEMEETER = 1
    BANANA = 2
    POTATO = 3


class VBANSampleRate(Enum):
    RATE_6000 = 0, 6000
    RATE_8000 = 7, 8000
    RATE_11025 = 14, 11025
    RATE_12000 = 1, 12000
    RATE_16000 = 8, 16000
    RATE_22050 = 15, 22050
    RATE_24000 = 2, 24000
    RATE_32000 = 9, 32000
    RATE_44100 = 16, 44100
    RATE_48000 = 3, 48000
    RATE_64000 = 10, 64000
    RATE_88200 = 17, 88200
    RATE_96000 = 4, 96000
    RATE_128000 = 11, 128000
    RATE_176400 = 18, 176400
    RATE_192000 = 5, 192000
    RATE_256000 = 12, 256000
    RATE_352800 = 19, 352800
    RATE_384000 = 6, 384000
    RATE_512000 = 13, 512000
    RATE_705600 = 20, 705600

    def __new__(cls, data, rate):
        obj = object.__new__(cls)
        obj.key = obj._value_ = data & 0x1F
        obj.rate = rate
        return obj

    @classmethod
    def find(cls, data: int) -> "VBANSampleRate":
        filtered_values = [r for r in VBANSampleRate if r.rate == data]
        if len(filtered_values) > 0:
            return filtered_values[0]
        return None

    def __int__(self) -> int:
        return self.key


class State(Flag):
    MODE_MUTE = 0x00000001
    MODE_SOLO = 0x00000002
    MODE_MONO = 0x00000004
    MODE_MUTEC = 0x00000008

    MODE_MIXDOWN = 0x00000010
    MODE_REPEAT = 0x00000020
    MODE_MIXDOWNB = 0x00000030
    MODE_COMPOSITE = 0x00000040
    MODE_UPMIXTV = 0x00000050
    MODE_UPMIX2 = 0x00000060
    MODE_UPMIX4 = 0x00000070
    MODE_UPMIX6 = 0x00000080
    MODE_CENTER = 0x00000090
    MODE_LFE = 0x000000A0
    MODE_REAR = 0x000000B0

    MODE_MASK = 0x000000F0

    MODE_EQ = 0x00000100
    MODE_CROSS = 0x00000200
    MODE_EQB = 0x00000800

    MODE_BUSA = 0x00001000
    MODE_BUSA1 = 0x00001000
    MODE_BUSA2 = 0x00002000
    MODE_BUSA3 = 0x00004000
    MODE_BUSA4 = 0x00008000
    MODE_BUSA5 = 0x00080000

    MODE_BUSB = 0x00010000
    MODE_BUSB1 = 0x00010000
    MODE_BUSB2 = 0x00020000
    MODE_BUSB3 = 0x00040000

    MODE_PAN0 = 0x00000000
    MODE_PANCOLOR = 0x00100000
    MODE_PANMOD = 0x00200000
    MODE_PANMASK = 0x00F00000

    MODE_POSTFX_R = 0x01000000
    MODE_POSTFX_D = 0x02000000
    MODE_POSTFX1 = 0x04000000
    MODE_POSTFX2 = 0x08000000

    MODE_SEL = 0x10000000
    MODE_MONITOR = 0x20000000

    def __int__(self):
        return int(self.value)


class VBANBaudRate(Enum):
    RATE_0 = 0
    RATE_110 = 1
    RATE_150 = 2
    RATE_300 = 3
    RATE_600 = 4
    RATE_1200 = 5
    RATE_2400 = 6
    RATE_4800 = 7
    RATE_9600 = 8
    RATE_14400 = 9
    RATE_19200 = 10
    RATE_31250 = 11
    RATE_38400 = 12
    RATE_57600 = 13
    RATE_115200 = 14
    RATE_128000 = 15
    RATE_230400 = 16
    RATE_250000 = 17
    RATE_256000 = 18
    RATE_460800 = 19
    RATE_921600 = 20
    RATE_1000000 = 21
    RATE_1500000 = 22
    RATE_2000000 = 23
    RATE_3000000 = 24
    RATE_UNDEFINED1 = 25
    RATE_UNDEFINED2 = 26
    RATE_UNDEFINED3 = 27
    RATE_UNDEFINED4 = 28
    RATE_UNDEFINED5 = 29
    RATE_UNDEFINED6 = 30
    RATE_UNDEFINED7 = 31

    def __new__(cls, data):
        obj = object.__new__(cls)
        obj.key = obj._value_ = data & 0x1F
        return obj

    def __int__(self) -> int:
        return self.key


class DeviceType(Flag):
    Unknown = 0x00000000
    Receptor = 0x00000001
    Transmitter = 0x00000002
    ReceptorSpot = 0x00000004
    TransmitterSpot = 0x00000008
    VirtualDevice = 0x00000010
    VirtualMixer = 0x00000020
    Matrix = 0x00000040
    DAW = 0x00000080
    Server = 0x01000000


class Features(Flag):
    NoFeatures = 0x00000000
    Audio = 0x00000001
    AoIP = 0x00000002
    VoIP = 0x00000004
    Serial = 0x00000100
    MIDI = 0x00000300
    Frame = 0x00001000
    Text = 0x00010000
