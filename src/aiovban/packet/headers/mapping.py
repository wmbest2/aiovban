from enum import EnumMeta, Enum

from ...packet.headers.audio import VBANAudioHeader
from ...packet.headers.service import VBANServiceHeader
from ...packet.headers.subprotocol import VBANSubProtocolTypes
from ...packet.headers.text import VBANTextHeader


class VBANSubProtocolMappingMeta(EnumMeta):

    def __call__(cls, value, **kwargs):
        return super().__call__(VBANSubProtocolTypes(value), **kwargs)

class VBANSubProtocolMapping(Enum, metaclass=VBANSubProtocolMappingMeta):
    AUDIO = VBANSubProtocolTypes.AUDIO, VBANAudioHeader
    SERIAL = VBANSubProtocolTypes.SERIAL
    TEXT = VBANSubProtocolTypes.TEXT, VBANTextHeader
    SERVICE = VBANSubProtocolTypes.SERVICE, VBANServiceHeader
    UNDEFINED_1 = VBANSubProtocolTypes.UNDEFINED_1
    UNDEFINED_2 = VBANSubProtocolTypes.UNDEFINED_2
    UNDEFINED_3 = VBANSubProtocolTypes.UNDEFINED_3
    USER = VBANSubProtocolTypes.USER


    def __new__(cls, type_data, header_type=None):
        obj = object.__new__(cls)
        obj.type = obj._value_ = type_data
        obj.header_type = header_type
        return obj