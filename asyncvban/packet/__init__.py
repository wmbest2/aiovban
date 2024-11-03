from dataclasses import dataclass

from ..packet.headers import VBANHeader


@dataclass
class VBANPacket:
    header: VBANHeader
    body: bytes = b""

    def pack(self):
        return self.header.pack() + self.body

    @classmethod
    def unpack(cls, data):
        header = VBANHeader.unpack(data)
        return VBANPacket(header, data[28:])