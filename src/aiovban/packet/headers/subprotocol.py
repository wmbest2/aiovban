from enum import EnumMeta, IntEnum


class VBANSubProtocolTypesMeta(EnumMeta):

    def __call__(cls, value, **kwargs):
        return super().__call__(value & 0xE0, **kwargs)


class VBANSubProtocolTypes(IntEnum, metaclass=VBANSubProtocolTypesMeta):
    AUDIO = 0x00
    SERIAL = 0x20
    TEXT = 0x40
    SERVICE = 0x60
    UNDEFINED_1 = 0x80
    UNDEFINED_2 = 0xA0
    UNDEFINED_3 = 0xC0
    USER = 0xE0
