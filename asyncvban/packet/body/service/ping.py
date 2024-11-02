import struct
from dataclasses import dataclass, field
from enum import Flag

from asyncvban.enums import VBANSampleRate


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
class Ping:
    deviceType: DeviceType
    features: Features
    featureExtra: int
    colorRGB: str
    version: str
    preferredRate: VBANSampleRate = None
    minRate: VBANSampleRate = VBANSampleRate.RATE_6000
    maxRate: VBANSampleRate = VBANSampleRate.RATE_705600
    gpsPosition: str = ""
    userPosition: str = ""
    langCode: str = ""
    reserved: str = field(repr=False, default="")
    reservedEx: str = field(repr=False, default="")
    distantIP: str = ""
    distantPort: int = 0
    distantReserved: int = 0
    deviceName: str = ""
    manufacturerName: str = ""
    applicationName: str = ""
    hostName: str = ""
    userName: str = ""
    userComment: str = ""

    def pack(self):
        version_codes = self.version.split('.')
        return struct.pack(
            PING_STRUCT_FORMAT,
            self.deviceType.value,
            self.features.value,
            self.featureExtra,
            int(self.preferredRate) if self.preferredRate else 0,
            int(self.minRate) if self.preferredRate else 0,
            int(self.maxRate) if self.preferredRate else 0,
            int(self.colorRGB, 16),
            *[ int(version_codes[i]) if i < len(version_codes) else 0 for i in range(4)],
            self.gpsPosition.encode('ascii'),
            self.userPosition.encode('ascii'),
            self.langCode.encode('ascii'),
            self.reserved.encode('ascii'),
            self.reservedEx.encode('ascii'),
            self.distantIP.encode('ascii'),
            self.distantPort,
            self.distantReserved,
            self.deviceName.encode('ascii'),
            self.manufacturerName.encode('ascii'),
            self.applicationName.encode('ascii'),
            self.hostName.encode('ascii'),
            self.userName.encode('utf-8'),
            self.userComment.encode('utf-8')
        )

    @classmethod
    def unpack(cls, data):
        unpacked_data = struct.unpack(
            PING_STRUCT_FORMAT, data
        )
        return cls(
            deviceType=DeviceType(unpacked_data[0]),
            features=Features(unpacked_data[1]),
            featureExtra=unpacked_data[2],
            preferredRate=VBANSampleRate.find(unpacked_data[3]),
            minRate=VBANSampleRate.find(unpacked_data[4]),
            maxRate=VBANSampleRate.find(unpacked_data[5]),
            colorRGB=hex(unpacked_data[6]),
            version=f"{unpacked_data[10]}.{unpacked_data[9]}.{unpacked_data[8]}.{unpacked_data[7]}",
            gpsPosition=unpacked_data[11].decode('ascii').strip('\x00'),
            userPosition=unpacked_data[12].decode('ascii').strip('\x00'),
            langCode=unpacked_data[13].decode('ascii').strip('\x00'),
            reserved=unpacked_data[14],
            reservedEx=unpacked_data[15],
            distantIP=unpacked_data[16].decode('ascii').strip('\x00'),
            distantPort=unpacked_data[17],
            distantReserved=unpacked_data[18],
            deviceName=unpacked_data[19].decode('ascii').strip('\x00'),
            manufacturerName=unpacked_data[20].decode('ascii').strip('\x00'),
            applicationName=unpacked_data[21].decode('ascii').strip('\x00'),
            hostName=unpacked_data[22].decode('ascii').strip('\x00'),
            userName=unpacked_data[23].decode('utf-8').strip('\x00'),
            userComment=unpacked_data[24].decode('utf-8').strip('\x00')
        )