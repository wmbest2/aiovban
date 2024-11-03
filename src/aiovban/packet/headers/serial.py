from dataclasses import dataclass

from . import VBANHeader
from .subprotocol import VBANSubProtocolTypes
from ...enums import VBANBaudRate
from ...util.synthetics import subprotocol_data, byte_a, byte_c, byte_b, subprotocol


class StopBit:
    ONE = 0x00
    ONE_POINT_FIVE = 0x01
    TWO = 0x02


class StartBit:
    NO_START_BIT = 0x00
    START_BIT = 0x01 << 2


class DataFormat:
    Data_8Bit = 0x00
    Undefined1 = 0x01
    Undefined2 = 0x02
    Undefined3 = 0x03
    Undefined4 = 0x04
    Undefined5 = 0x05
    Undefined6 = 0x06
    Undefined7 = 0x07


class SerialType:
    Generic = 0x00
    Midi = 0x10
    Undefined2 = 0x20
    Undefined3 = 0x30
    Undefined4 = 0x40
    Undefined5 = 0x50
    Undefined6 = 0x60
    Undefined7 = 0x70
    Undefined8 = 0x80
    Undefined9 = 0x90
    Undefined10 = 0xA0
    Undefined11 = 0xB0
    Undefined12 = 0xC0
    Undefined13 = 0xD0
    Undefined14 = 0xE0
    User = 0xF0


@dataclass
class VBANSerialHeader(VBANHeader):
    baud: VBANBaudRate = subprotocol_data()

    channel: int = byte_b(default=0)

    stop_bit: StopBit = byte_a(0x03, default=0)
    start_bit: bool = byte_a(0x04, default=False)
    parity_checking: bool = byte_a(0x08, default=False)
    multipart_data: bool = byte_a(0x80, default=False)
    format: DataFormat = byte_c(0x07, default=DataFormat.Data_8Bit)
    serial_type: SerialType = byte_c(0x07, default=SerialType.Generic)
    _: VBANSubProtocolTypes = subprotocol(VBANSubProtocolTypes.SERIAL)
