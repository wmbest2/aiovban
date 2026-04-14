import unittest
from unittest.mock import MagicMock
from aiovban.asyncio.voicemeeter import VoicemeeterRemote, VoicemeeterStrip, VoicemeeterBus
from aiovban.enums import VoicemeeterType, BusMode, State
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0, Strip, Bus

class TestVoicemeeterPackage(unittest.TestCase):
    def setUp(self):
        self.mock_device = MagicMock()
        self.remote = VoicemeeterRemote(self.mock_device)

    def test_imports(self):
        """Test that everything is correctly exported from the package."""
        from aiovban.asyncio.voicemeeter import VoicemeeterRemote, VoicemeeterStrip, VoicemeeterBus, VoicemeeterBase
        self.assertIsNotNone(VoicemeeterRemote)
        self.assertIsNotNone(VoicemeeterStrip)
        self.assertIsNotNone(VoicemeeterBus)
        self.assertIsNotNone(VoicemeeterBase)

    def test_strip_knobs(self):
        """Test compressor, gate, and denoiser on strips."""
        strip = self.remote._all_strips[0]
        # These are just state storage for now as they aren't in RT packets
        strip.compressor = 5.0
        strip.gate = 2.5
        strip.denoiser = 1.0
        
        self.assertEqual(strip.compressor, 5.0)
        self.assertEqual(strip.gate, 2.5)
        self.assertEqual(strip.denoiser, 1.0)

    def test_mono_state(self):
        """Test mono state on strips and buses."""
        strip = self.remote._all_strips[0]
        bus = self.remote._all_buses[0]
        
        strip.mono = True
        bus.mono = True
        
        self.assertTrue(strip.mono)
        self.assertTrue(bus.mono)

    def test_bus_mode(self):
        """Test bus mode."""
        bus = self.remote._all_buses[0]
        bus.mode = BusMode.REPEAT
        self.assertEqual(bus.mode, BusMode.REPEAT)

    def test_apply_rt_packet_sync(self):
        """Test that apply_rt_packet correctly syncs mono and bus mode."""
        body = MagicMock(spec=RTPacketBodyType0)
        body.voice_meeter_type = VoicemeeterType.BANANA
        body.voice_meeter_version = "2.0.5.3"
        body.transport_bits = 0
        body.input_levels = [0] * 34
        body.output_levels = [0] * 64

        # Create mock strips with mono bit set

        mock_strips = []
        for i in range(8):
            s = MagicMock(spec=Strip)
            s.label = f"Strip{i}"
            s.state = State.MODE_MONO | State.MODE_MUTE if i == 0 else State.MODE_MUTE
            s.layers = [0] * 8
            mock_strips.append(s)
        body.strips = mock_strips

        # Create mock buses with mono bit and different modes
        mock_buses = []
        for i in range(8):
            b = MagicMock(spec=Bus)
            b.label = f"Bus{i}"
            # BusMode.REPEAT = 3
            # (3 << 4) = 0x30 = State.MODE_MIXDOWNB (in current enums)
            if i == 0:
                b.state = State.MODE_MONO | State.MODE_MIXDOWNB
            else:
                b.state = State(0)
            b.gain = 0
            mock_buses.append(b)
        body.buses = mock_buses

        self.remote.apply_rt_packet(body)

        # Check Strip 0
        self.assertTrue(self.remote._all_strips[0].mono)
        self.assertTrue(self.remote._all_strips[0].mute)
        
        # Check Strip 1
        self.assertFalse(self.remote._all_strips[1].mono)

        # Check Bus 0
        self.assertTrue(self.remote._all_buses[0].mono)
        self.assertEqual(self.remote._all_buses[0].mode, BusMode.REPEAT)

        # Check Bus 1
        self.assertFalse(self.remote._all_buses[1].mono)
        self.assertEqual(self.remote._all_buses[1].mode, BusMode.NORMAL)

if __name__ == "__main__":
    unittest.main()
