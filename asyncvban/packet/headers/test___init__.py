from unittest import TestCase

from ...packet.headers import VBANHeader
from ...packet.headers.audio import VBANAudioHeader
from ...enums import VBANSampleRate
from ...packet.headers.service import VBANServiceHeader
from ...packet.headers.subprotocol import VBANSubProtocolTypes


class TestVBANSubProtocol(TestCase):

    def test_enum_search(self):
        data = 0x00 | int(VBANSampleRate.RATE_44100)
        sub = VBANSubProtocolTypes(data)


        self.assertIs(type(sub), VBANSubProtocolTypes)

        vh = VBANAudioHeader(sample_rate=VBANSampleRate.RATE_44100, channels=17, samples_per_frame=3, bit_resolution=3, codec=0xf0, streamname="Channel1")
        print(VBANAudioHeader.pack(vh))
        output = VBANAudioHeader.unpack(VBANHeader.pack(vh))
        print(type(output.sample_rate))


        vs = VBANServiceHeader(function=0x00, service=0x20)
        print(VBANHeader.pack(vs))
        output = VBANHeader.unpack(VBANHeader.pack(vs))
        print(output)
