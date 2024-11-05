from dataclasses import dataclass

from aiovban.enums import DeviceType, Features, VBANSampleRate


@dataclass
class VBANApplicationData:
    device_type: DeviceType
    features: Features
    version: str
    color_rgb: str = "0x000000"
    preferred_rate: VBANSampleRate = None
    min_rate: VBANSampleRate = VBANSampleRate.RATE_6000
    max_rate: VBANSampleRate = VBANSampleRate.RATE_705600
    lang_code: str = ""
    application_name: str = ""
    user_name: str = ""
    user_comment: str = ""
