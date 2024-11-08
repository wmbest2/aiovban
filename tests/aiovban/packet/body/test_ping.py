import unittest

from aiovban.enums import VBANSampleRate, DeviceType, Features
from aiovban.packet.body.service.ping import Ping


class TestPing(unittest.TestCase):

    def setUp(self):
        self.sample_data = {
            "device_type": DeviceType.Receptor,
            "features": Features.Audio | Features.Text,
            "feature_extra": 0,
            "preferred_rate": VBANSampleRate.RATE_44100,
            "min_rate": VBANSampleRate.RATE_22050,
            "max_rate": VBANSampleRate.RATE_48000,
            "color_rgb": "0xffffff",
            "version": "1.0.0.0",
            "gps_position": "GPS",
            "user_position": "UserPos",
            "lang_code": "EN",
            "reserved": "",
            "reserved_ex": "",
            "distant_ip": "192.168.1.1",
            "distant_port": 6980,
            "distant_reserved": 0,
            "device_name": "Device",
            "manufacturer_name": "Manufacturer",
            "application_name": "App",
            "host_name": "Host",
            "user_name": "User",
            "user_comment": "Comment"
        }
        self.ping = Ping(**self.sample_data)

    def test_pack_unpack(self):
        packed_data = self.ping.pack()
        unpacked_ping = Ping.unpack(packed_data)

        self.assertEqual(unpacked_ping.device_type, self.sample_data["device_type"])
        self.assertEqual(unpacked_ping.features, self.sample_data["features"])
        self.assertEqual(unpacked_ping.feature_extra, self.sample_data["feature_extra"])
        self.assertEqual(unpacked_ping.preferred_rate, self.sample_data["preferred_rate"])
        self.assertEqual(unpacked_ping.min_rate, self.sample_data["min_rate"])
        self.assertEqual(unpacked_ping.max_rate, self.sample_data["max_rate"])
        self.assertEqual(unpacked_ping.color_rgb, self.sample_data["color_rgb"])
        self.assertEqual(unpacked_ping.version, self.sample_data["version"])
        self.assertEqual(unpacked_ping.gps_position, self.sample_data["gps_position"])
        self.assertEqual(unpacked_ping.user_position, self.sample_data["user_position"])
        self.assertEqual(unpacked_ping.lang_code, self.sample_data["lang_code"])
        self.assertEqual(unpacked_ping.distant_ip, self.sample_data["distant_ip"])
        self.assertEqual(unpacked_ping.distant_port, self.sample_data["distant_port"])
        self.assertEqual(unpacked_ping.distant_reserved, self.sample_data["distant_reserved"])
        self.assertEqual(unpacked_ping.device_name, self.sample_data["device_name"])
        self.assertEqual(unpacked_ping.manufacturer_name, self.sample_data["manufacturer_name"])
        self.assertEqual(unpacked_ping.application_name, self.sample_data["application_name"])
        self.assertEqual(unpacked_ping.host_name, self.sample_data["host_name"])
        self.assertEqual(unpacked_ping.user_name, self.sample_data["user_name"])
        self.assertEqual(unpacked_ping.user_comment, self.sample_data["user_comment"])

if __name__ == '__main__':
    unittest.main()