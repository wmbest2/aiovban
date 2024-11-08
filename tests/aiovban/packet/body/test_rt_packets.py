import unittest
import random


from aiovban.enums import VBANSampleRate, State, VoicemeeterType
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0, Bus, Strip


def generate_random_levels(num_levels):
    return [random.randint(0, 65535) for _ in range(num_levels)]

def generate_random_state():
    flags = [flag for flag in State]
    num_flags = random.randint(1, len(flags))
    selected_flags = random.sample(flags, num_flags)
    random_state = selected_flags[0]
    for flag in selected_flags[1:]:
        random_state |= flag
    return random_state


class TestRTPacketBodyType0(unittest.TestCase):

    def setUp(self):
        self.sample_data = {
            "voice_meeter_type": VoicemeeterType(1),
            "buffer_size": 512,
            "voice_meeter_version": "2.0.0.0",
            "sample_rate": VBANSampleRate.RATE_44100,
            "input_levels": generate_random_levels(34),
            "output_levels": generate_random_levels(64),
            "transport_bits": 0,
            "strips": [
                Strip(label=f"Strip {i}" + "-"*random.randint(0, 100), state=generate_random_state(), layers=generate_random_levels(8)) for i in range(8)
            ],
            "buses": [
                Bus(label=f"Bus {i}" + "-"*random.randint(0, 100), state=generate_random_state(), gain=random.randint(0, 65535)) for i in range(8)
            ]
        }
        self.rt_packet = RTPacketBodyType0(**self.sample_data)

    def test_pack_unpack(self):
        packed_data = self.rt_packet.pack()
        unpacked_rt_packet = RTPacketBodyType0.unpack(packed_data)

        self.assertEqual(unpacked_rt_packet.voice_meeter_type, self.sample_data["voice_meeter_type"])
        self.assertEqual(unpacked_rt_packet.buffer_size, self.sample_data["buffer_size"])
        self.assertEqual(unpacked_rt_packet.voice_meeter_version, self.sample_data["voice_meeter_version"])
        self.assertEqual(unpacked_rt_packet.sample_rate, self.sample_data["sample_rate"])
        self.assertEqual(unpacked_rt_packet.input_levels, self.sample_data["input_levels"])
        self.assertEqual(unpacked_rt_packet.output_levels, self.sample_data["output_levels"])
        self.assertEqual(unpacked_rt_packet.transport_bits, self.sample_data["transport_bits"])
        self.assertEqual(len(unpacked_rt_packet.strips), len(self.sample_data["strips"]))
        self.assertEqual(len(unpacked_rt_packet.buses), len(self.sample_data["buses"]))

        for i in range(8):
            # Truncate the label to 60 characters since that's the maximum length
            self.assertEqual(unpacked_rt_packet.strips[i].label, self.sample_data["strips"][i].label[:60])
            self.assertEqual(unpacked_rt_packet.strips[i].state, self.sample_data["strips"][i].state)
            self.assertEqual(unpacked_rt_packet.strips[i].layers, self.sample_data["strips"][i].layers)
            # Truncate the label to 60 characters since that's the maximum length
            self.assertEqual(unpacked_rt_packet.buses[i].label, self.sample_data["buses"][i].label[:60])
            self.assertEqual(unpacked_rt_packet.buses[i].state, self.sample_data["buses"][i].state)
            self.assertEqual(unpacked_rt_packet.buses[i].gain, self.sample_data["buses"][i].gain)

if __name__ == '__main__':
    unittest.main()