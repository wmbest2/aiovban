from dataclasses import dataclass
from enum import IntEnum

from . import VBANHeader
from .subprotocol import VBANSubProtocolTypes
from ...enums import VBANSampleRate
from ...util.synthetics import subprotocol_data, byte_a, byte_b, byte_c, subprotocol

class BitResolution(IntEnum):
    BYTE8 = 0x00
    INT16 = 0x01
    INT24 = 0x02
    INT32 = 0x03
    FLOAT32 = 0x04
    FLOAT64 = 0x05
    BITS12 = 0x06
    BITS10 = 0x07

    def __int__(self):
        return self.value

class Codec(IntEnum):
    PCM = 0x00
    VBCA = 0x10
    VBCV = 0x20
    UNDEFINED_1 = 0x30
    UNDEFINED_2 = 0x40
    UNDEFINED_3 = 0x50
    UNDEFINED_4 = 0x60
    UNDEFINED_5 = 0x70
    UNDEFINED_6 = 0x80
    UNDEFINED_7 = 0x90
    UNDEFINED_8 = 0xA0
    UNDEFINED_9 = 0xB0
    UNDEFINED_10 = 0xC0
    UNDEFINED_11 = 0xD0
    UNDEFINED_12 = 0xE0
    USER = 0xF0


@dataclass
class VBANAudioHeader(VBANHeader):
    samples_per_frame: int = byte_a()
    channels: int = byte_b(offset=1)
    bit_resolution: BitResolution = byte_c(0x07)
    codec: Codec = byte_c(0xF0)

    sample_rate: VBANSampleRate = subprotocol_data()
    _: VBANSubProtocolTypes = subprotocol(VBANSubProtocolTypes.AUDIO)
