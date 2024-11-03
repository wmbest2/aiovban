from dataclasses import dataclass
from enum import IntEnum

from ...enums import VBANBaudRate
from ...packet.headers import VBANHeader, VBANSubProtocolTypes
from ...util.synthetics import subprotocol_data, byte_c, byte_b, subprotocol

class VBANTextStreamType(IntEnum):
    ASCII       = 0x00
    UTF_8       = 0x10
    WCHAR       = 0x20
    UNDEFINED1  = 0x30
    UNDEFINED2  = 0x40
    UNDEFINED3  = 0x50
    UNDEFINED4  = 0x60
    UNDEFINED5  = 0x70
    UNDEFINED6  = 0x80
    UNDEFINED7  = 0x90
    UNDEFINED8  = 0xA0
    UNDEFINED9  = 0xB0
    UNDEFINED10 = 0xC0
    UNDEFINED11 = 0xD0
    UNDEFINED12 = 0xE0
    USER        = 0xF0



@dataclass
class VBANTextHeader(VBANHeader):
    baud: VBANBaudRate = subprotocol_data()

    channel: int = byte_b(default=0)
    format_bit: int = byte_c(0x07, default=0)
    stream_type: VBANTextStreamType = byte_c(0xF0, default=int(VBANTextStreamType.UTF_8))
    _: VBANSubProtocolTypes = subprotocol(VBANSubProtocolTypes.TEXT)
