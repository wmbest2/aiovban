import struct
from dataclasses import dataclass, field

from .subprotocol import VBANSubProtocolTypes
from ...util.synthetics import SyntheticMixin


_STREAMNAME_CACHE = {}


_STREAMNAME_PACK_CACHE = {}


@dataclass(kw_only=True)
class VBANHeader(SyntheticMixin):
    framecount: int = 0
    subprotocol: VBANSubProtocolTypes = None
    streamname: str = field(default="Command1")

    _SUBCLASSES = {}

    @classmethod
    def register_subclass(cls, subprotocol: VBANSubProtocolTypes):
        def wrapper(subclass):
            cls._SUBCLASSES[subprotocol] = subclass
            return subclass
        return wrapper

    def pack(self) -> bytes:
        # Cache encoded and padded stream name
        stream_bytes = _STREAMNAME_PACK_CACHE.get(self.streamname)
        if stream_bytes is None:
            stream = self.streamname[:16].encode("utf-8")
            stream_bytes = stream.ljust(16, b"\x00")
            if len(_STREAMNAME_PACK_CACHE) < 128:
                _STREAMNAME_PACK_CACHE[self.streamname] = stream_bytes

        return struct.pack(
            "<4sBBBB16sL",
            b"VBAN",
            (self.subprotocol or 0) | getattr(self, "subprotocol_data", 0),
            getattr(self, "byte_a", 0),
            getattr(self, "byte_b", 0),
            getattr(self, "byte_c", 0),
            stream_bytes,
            self.framecount,
        )

    @classmethod
    def unpack(cls, data: bytes):
        # Validate minimum header size
        if len(data) < 28:
            raise VBANHeaderException(
                f"Insufficient data for VBAN header: expected at least 28 bytes, got {len(data)}"
            )

        if data[0:4] != b"VBAN":
            raise VBANHeaderException("Invalid VBAN Header")

        sub, sub_data = data[4] & 0xE0, data[4] & 0x1F

        subclass = cls._SUBCLASSES.get(sub, cls)
        obj = cls.__new__(subclass)  # Create bare type
        obj.__post_init__()  # Initialize synthetic properties
        obj.subprotocol = sub
        obj.subprotocol_data = sub_data
        obj.byte_a = data[5]
        obj.byte_b = data[6]
        obj.byte_c = data[7]

        # Safely decode streamname with error handling, using a cache to avoid redundant decoding
        streamname_bytes = data[8:24]
        if streamname_bytes in _STREAMNAME_CACHE:
            obj.streamname = _STREAMNAME_CACHE[streamname_bytes]
        else:
            obj.streamname = streamname_bytes.split(b"\x00", 1)[0].decode("utf-8")
            if len(_STREAMNAME_CACHE) < 128:
                _STREAMNAME_CACHE[streamname_bytes] = obj.streamname

        try:
            obj.framecount = struct.unpack("<L", data[24:28])[0]
        except struct.error as e:
            raise VBANHeaderException(f"Failed to unpack framecount: {e}")
        return obj


class VBANHeaderException(Exception):
    pass
