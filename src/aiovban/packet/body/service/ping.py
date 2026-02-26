import struct
from dataclasses import dataclass, field

from .. import PacketBody
from .... import VBANApplicationData
from ....enums import VBANSampleRate, DeviceType, Features

# PING_STRUCT_FORMAT:
# Using '=' ensures exact offsets as in the capture.
# 7L: 28 bytes
# 4B: 4 bytes (Total 32)
# 8s: gps (Total 40)
# 8s: userpos (Total 48)
# 8s: lang_code (Total 56)
# 8s: reserved (Total 64)
# 64s: reserved_ex (Total 128)
# 32s: distant_ip (Total 160)
# H: distant_port (Total 162)
# H: distant_reserved (Total 164)
# 64s: device_name (Total 228)
# 64s: manufacturer_name (Total 292)
# 64s: application_name (Total 356)
# 64s: host_name (Total 420)
# 128s: user_name (Total 548)
# 128s: user_comment (Total 676)
PING_STRUCT_FORMAT = "<LLLLLLLBBBB8s8s8s8s64s32sHH64s64s64s64s128s128s"

@dataclass
class Ping(PacketBody, VBANApplicationData):
    feature_extra: int = 0
    gps_position: str = ""
    user_position: str = ""
    reserved: str = field(repr=False, default="")
    reserved_ex: str = field(repr=False, default="")
    distant_ip: str = ""
    distant_port: int = 0
    distant_reserved: int = 0
    device_name: str = ""
    manufacturer_name: str = ""
    host_name: str = ""

    def pack(self):
        version_codes = self.version.split(".")
        return struct.pack(
            PING_STRUCT_FORMAT,
            self.device_type.value,
            self.features.value,
            self.feature_extra,
            self.preferred_rate.rate if self.preferred_rate else 0,
            self.min_rate.rate if self.min_rate else 0,
            self.max_rate.rate if self.max_rate else 0,
            int(self.color_rgb, 16),
            *[
                int(version_codes[3 - i]) if (3 - i) < len(version_codes) else 0
                for i in range(4)
            ],
            self.gps_position.encode("ascii")[:8].ljust(8, b"\x00"),
            self.user_position.encode("ascii")[:8].ljust(8, b"\x00"),
            self.lang_code.encode("ascii")[:8].ljust(8, b"\x00"),
            self.reserved.encode("ascii")[:8].ljust(8, b"\x00"),
            self.reserved_ex.encode("ascii")[:64].ljust(64, b"\x00"),
            self.distant_ip.encode("ascii")[:32].ljust(32, b"\x00"),
            self.distant_port,
            self.distant_reserved,
            self.device_name.encode("ascii")[:64].ljust(64, b"\x00"),
            self.manufacturer_name.encode("ascii")[:64].ljust(64, b"\x00"),
            self.application_name.encode("ascii")[:64].ljust(64, b"\x00"),
            self.host_name.encode("ascii")[:64].ljust(64, b"\x00"),
            self.user_name.encode("utf-8")[:128].ljust(128, b"\x00"),
            self.user_comment.encode("utf-8")[:128].ljust(128, b"\x00"),
        )

    @classmethod
    def unpack(cls, data):
        expected_size = struct.calcsize(PING_STRUCT_FORMAT)
        if len(data) < expected_size:
            data = data.ljust(expected_size, b"\x00")

        unpacked_data = struct.unpack(PING_STRUCT_FORMAT, data[:expected_size])

        return cls(
            device_type=DeviceType(unpacked_data[0]),
            features=Features(unpacked_data[1]),
            feature_extra=unpacked_data[2],
            preferred_rate=VBANSampleRate.find(unpacked_data[3]),
            min_rate=VBANSampleRate.find(unpacked_data[4]),
            max_rate=VBANSampleRate.find(unpacked_data[5]),
            color_rgb=hex(unpacked_data[6]),
            version=f"{unpacked_data[10]}.{unpacked_data[9]}.{unpacked_data[8]}.{unpacked_data[7]}",
            gps_position=unpacked_data[11].decode("ascii").strip("\x00"),
            user_position=unpacked_data[12].decode("ascii").strip("\x00"),
            lang_code=unpacked_data[13].decode("ascii").strip("\x00"),
            reserved=unpacked_data[14].decode("ascii", errors="replace").strip("\x00"),
            reserved_ex=unpacked_data[15].decode("ascii", errors="replace").strip("\x00"),
            distant_ip=unpacked_data[16].decode("ascii").strip("\x00"),
            distant_port=unpacked_data[17],
            distant_reserved=unpacked_data[18],
            device_name=unpacked_data[19].decode("ascii").strip("\x00"),
            manufacturer_name=unpacked_data[20].decode("ascii").strip("\x00"),
            application_name=unpacked_data[21].decode("ascii").strip("\x00"),
            host_name=unpacked_data[22].decode("ascii").strip("\x00"),
            user_name=unpacked_data[23].decode("utf-8").strip("\x00"),
            user_comment=unpacked_data[24].decode("utf-8").strip("\x00"),
        )
