from dataclasses import dataclass
from enum import IntEnum

from . import VBANHeader
from .subprotocol import VBANSubProtocolTypes
from ...util.synthetics import byte_a, byte_b, subprotocol, byte_c

class ServiceType(IntEnum):
    Identification = 0x00
    Chat_UTF8 = 0x01
    RTPacketRegister = 0x20
    RTPacket = 0x21

    def __int__(self):
        return self.value

class PingFunctions(IntEnum):
    Request = 0x00
    Response = 0x80

    def __int__(self):
        return self.value


@dataclass
class VBANServiceHeader(VBANHeader):
    service: ServiceType = byte_b()

    function: int = byte_a(default=0x00)
    additional_info: int = byte_c(default=0x00)
    _: VBANSubProtocolTypes = subprotocol(VBANSubProtocolTypes.SERVICE)
