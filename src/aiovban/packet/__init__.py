from dataclasses import dataclass

from .headers import VBANSubProtocolTypes
from .body import PacketBody, BytesBody
from .headers import VBANHeader
from .headers.service import VBANServiceHeader, ServiceType


@dataclass
class VBANPacket:
    header: VBANHeader
    body: PacketBody = BytesBody(b"")

    def __post_init__(self):
        if isinstance(self.body, bytes):
            self.body = BytesBody(self.body)

    def pack(self):
        return self.header.pack() + self.body.pack()

    @classmethod
    def unpack(cls, data):
        header = VBANHeader.unpack(data)
        if isinstance(header, VBANServiceHeader):
            if header.service == ServiceType.Identification:
                from .body.service import Ping

                return VBANPacket(header, Ping.unpack(data[28:]))
            elif header.service == ServiceType.RTPacket:
                from .body.service import RTPacketBodyType0

                if header.function == 0x00:
                    return VBANPacket(header, RTPacketBodyType0.unpack(data[28:]))
            elif header.service == ServiceType.Chat_UTF8:
                from .body import Utf8StringBody

                return VBANPacket(header, Utf8StringBody.unpack(data[28:]))

        # Default/fallback to BytesBody
        return VBANPacket(header, BytesBody.unpack(data[28:]))
