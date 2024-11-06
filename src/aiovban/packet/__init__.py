import time
from dataclasses import dataclass

from .body import PacketBody, BytesBody
from .headers import VBANHeader
from .headers.subprotocol import VBANSubProtocolTypes
from .headers.service import VBANServiceHeader, ServiceType
from .headers.text import VBANTextHeader


@dataclass
class VBANPacket:
    header: VBANHeader
    body: PacketBody = BytesBody(b"")
    timestamp: int = 0

    def __post_init__(self):
        if isinstance(self.body, bytes):
            self.body = BytesBody(self.body)

    def pack(self):
        return self.header.pack() + self.body.pack()

    @property
    def latency(self):
        return time.time_ns() - self.timestamp

    @classmethod
    def unpack(cls, data):
        from .body import Utf8StringBody

        header = VBANHeader.unpack(data)
        if isinstance(header, VBANServiceHeader):
            if header.service == ServiceType.Identification:
                from .body.service import Ping

                return VBANPacket(header, Ping.unpack(data[28:]), timestamp=time.time_ns())
            elif header.service == ServiceType.RTPacket:
                from .body.service import RTPacketBodyType0

                if header.function == 0x00:
                    return VBANPacket(header, RTPacketBodyType0.unpack(data[28:]), timestamp=time.time_ns())
            elif header.service == ServiceType.Chat_UTF8:
                return VBANPacket(header, Utf8StringBody.unpack(data[28:]), timestamp=time.time_ns())

        elif isinstance(header, VBANTextHeader):
            return VBANPacket(header, Utf8StringBody.unpack(data[28:]), timestamp=time.time_ns())

        # Default/fallback to BytesBody
        return VBANPacket(header, BytesBody.unpack(data[28:]), timestamp=time.time_ns())
