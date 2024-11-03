import struct
from dataclasses import dataclass, field

from ...packet.headers.subprotocol import VBANSubProtocolTypes
from ...util.synthetics import SyntheticMixin


@dataclass(kw_only=True)
class VBANHeader(SyntheticMixin):
    framecount: int = 0
    subprotocol: VBANSubProtocolTypes = None
    streamname: str = field(default="Command1")

    def pack(self) -> bytes:
        output = b"VBAN"
        print(f"subprotocol: {self.subprotocol}, subprotocol_data: {getattr(self, 'subprotocol_data', 0)}")
        output += struct.pack("<B", self.subprotocol | getattr(self, 'subprotocol_data', 0))
        output += struct.pack("<B", getattr(self, 'byte_a', 0))
        output += struct.pack("<B", getattr(self, 'byte_b', 0))
        output += struct.pack("<B", getattr(self, 'byte_c', 0))
        stream = self.streamname[:16]
        output += bytes(stream + "\x00" * (16 - len(stream)), 'utf-8')
        output += struct.pack("<L", self.framecount)
        return output

    @classmethod
    def unpack(cls, data: bytes):
        (sub, sub_data) = data[4] & 0xE0, data[4] & 0x1F
        from ...packet.headers.mapping import VBANSubProtocolMapping
        subclass = VBANSubProtocolMapping(sub).header_type
        obj = cls.__new__(subclass) # Create bare type
        obj.__post_init__()         # Initialize synthetic properties
        obj.subprotocol = sub
        obj.subprotocol_data = sub_data
        obj.byte_a = data[5]
        obj.byte_b = data[6]
        obj.byte_c = data[7]
        obj.streamname = data[8:24].decode("utf-8").strip("\x00")
        obj.framecount = struct.unpack("<L", data[24:28])[0]
        return obj

    def unpack_body(self, data: bytes):
        pass
