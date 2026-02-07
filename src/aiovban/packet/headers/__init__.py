import struct
from dataclasses import dataclass, field

from .subprotocol import VBANSubProtocolTypes
from ...util.synthetics import SyntheticMixin


@dataclass(kw_only=True)
class VBANHeader(SyntheticMixin):
    framecount: int = 0
    subprotocol: VBANSubProtocolTypes = None
    streamname: str = field(default="Command1")

    def pack(self) -> bytes:
        output = b"VBAN"
        output += struct.pack(
            "<B", self.subprotocol | getattr(self, "subprotocol_data", 0)
        )
        output += struct.pack("<B", getattr(self, "byte_a", 0))
        output += struct.pack("<B", getattr(self, "byte_b", 0))
        output += struct.pack("<B", getattr(self, "byte_c", 0))
        stream = self.streamname[:16]
        output += bytes(stream + "\x00" * (16 - len(stream)), "utf-8")
        output += struct.pack("<L", self.framecount)
        return output

    @classmethod
    def unpack(cls, data: bytes):
        # Validate minimum header size
        if len(data) < 28:
            raise VBANHeaderException(f"Insufficient data for VBAN header: expected at least 28 bytes, got {len(data)}")
        
        (sub, sub_data) = data[4] & 0xE0, data[4] & 0x1F
        if data[0:4] != b"VBAN":
            raise VBANHeaderException("Invalid VBAN Header")
        from ...packet.headers.mapping import VBANSubProtocolMapping

        subclass = VBANSubProtocolMapping(sub).header_type
        obj = cls.__new__(subclass)  # Create bare type
        obj.__post_init__()  # Initialize synthetic properties
        obj.subprotocol = sub
        obj.subprotocol_data = sub_data
        obj.byte_a = data[5]
        obj.byte_b = data[6]
        obj.byte_c = data[7]
        # Safely decode streamname with error handling
        try:
            obj.streamname = data[8:24].split(b"\x00", 1)[0].decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 which accepts all byte values
            obj.streamname = data[8:24].split(b"\x00", 1)[0].decode("latin-1")
        try:
            obj.framecount = struct.unpack("<L", data[24:28])[0]
        except struct.error as e:
            raise VBANHeaderException(f"Failed to unpack framecount: {e}")
        return obj


class VBANHeaderException(Exception):
    pass
