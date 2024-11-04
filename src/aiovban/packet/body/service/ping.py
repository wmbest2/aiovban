import struct
from dataclasses import dataclass, field
from enum import Flag

from .. import PacketBody
from ....enums import VBANSampleRate


class DeviceType(Flag):
    Receptor = 0x00000001
    Transmitter = 0x00000002
    ReceptorSpot = 0x00000004
    TransmitterSpot = 0x00000008
    VirtualDevice = 0x00000010
    VirtualMixer = 0x00000020
    Matrix = 0x00000040
    DAW = 0x00000080
    Server = 0x01000000


class Features(Flag):
    Audio = 0x00000001
    AoIP = 0x00000002
    VoIP = 0x00000004
    Serial = 0x00000100
    MIDI = 0x00000300
    Frame = 0x00001000
    Text = 0x00010000


PING_STRUCT_FORMAT = "<LLLLLLLBBBB8s8s8s8s64s32sHH64s64s64s64s128s128s"


@dataclass
class Ping(PacketBody):
    device_type: DeviceType
    features: Features
    version: str

    feature_extra: int = 0
    color_rgb: str = "0x000000"
    preferred_rate: VBANSampleRate = None
    min_rate: VBANSampleRate = VBANSampleRate.RATE_6000
    max_rate: VBANSampleRate = VBANSampleRate.RATE_705600
    gps_position: str = ""
    user_position: str = ""
    lang_code: str = ""
    reserved: str = field(repr=False, default="")
    reserved_ex: str = field(repr=False, default="")
    distant_ip: str = ""
    distant_port: int = 0
    distant_reserved: int = 0
    device_name: str = ""
    manufacturer_name: str = ""
    application_name: str = ""
    host_name: str = ""
    user_name: str = ""
    user_comment: str = ""

    def pack(self):
        version_codes = self.version.split(".")
        return struct.pack(
            PING_STRUCT_FORMAT,
            self.device_type.value,
            self.features.value,
            self.feature_extra,
            int(self.preferred_rate) if self.preferred_rate else 0,
            int(self.min_rate) if self.preferred_rate else 0,
            int(self.max_rate) if self.preferred_rate else 0,
            int(self.color_rgb, 16),
            *[int(version_codes[i]) if i < len(version_codes) else 0 for i in range(4)],
            self.gps_position.encode("ascii"),
            self.user_position.encode("ascii"),
            self.lang_code.encode("ascii"),
            self.reserved.encode("ascii"),
            self.reserved_ex.encode("ascii"),
            self.distant_ip.encode("ascii"),
            self.distant_port,
            self.distant_reserved,
            self.device_name.encode("ascii"),
            self.manufacturer_name.encode("ascii"),
            self.application_name.encode("ascii"),
            self.host_name.encode("ascii"),
            self.user_name.encode("utf-8"),
            self.user_comment.encode("utf-8"),
        )

    @classmethod
    def unpack(cls, data):
        unpacked_data = struct.unpack(PING_STRUCT_FORMAT, data)
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
            reserved=unpacked_data[14],
            reserved_ex=unpacked_data[15],
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
