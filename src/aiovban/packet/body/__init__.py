from dataclasses import dataclass


@dataclass
class PacketBody:
    def pack(self):
        pass

    @classmethod
    def unpack(cls, data):
        pass


@dataclass
class BytesBody(PacketBody):
    data: bytes

    def __bytes__(self):
        return self.data

    def pack(self):
        return self.data

    @classmethod
    def unpack(cls, data):
        return cls(data)


@dataclass
class Utf8StringBody(PacketBody):
    text: str

    def __bytes__(self):
        return bytes(self.text, "utf-8")

    def pack(self):
        return bytes(self.text, "utf-8")

    @classmethod
    def unpack(cls, data):
        return cls(data.decode("utf-8"))
