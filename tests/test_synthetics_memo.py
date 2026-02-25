from aiovban.packet.headers.audio import VBANAudioHeader, BitResolution, Codec
from aiovban.enums import VBANSampleRate

def test_synthetic_memoization_behavior():
    h1 = VBANAudioHeader(
        samples_per_frame=1,
        channels=1,
        bit_resolution=BitResolution.INT16,
        codec=Codec.PCM,
        sample_rate=VBANSampleRate.RATE_44100,
        streamname="Test1"
    )
    
    # Check the base class VBANHeader (where subprotocol is defined)
    from aiovban.packet.headers import VBANHeader
    assert "subprotocol" in VBANHeader.__dict__
    prop1 = VBANHeader.__dict__["subprotocol"]
    
    h2 = VBANAudioHeader(
        samples_per_frame=1,
        channels=1,
        bit_resolution=BitResolution.INT16,
        codec=Codec.PCM,
        sample_rate=VBANSampleRate.RATE_44100,
        streamname="Test2"
    )
    
    prop2 = VBANHeader.__dict__["subprotocol"]
    assert prop1 is prop2
