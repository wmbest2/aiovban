import unittest
import asyncio
from unittest.mock import MagicMock, patch
from aiovban.asyncio.device import VBANDevice
from aiovban.asyncio.streams import VBANChatStream
from aiovban.packet import VBANPacket
from aiovban.packet.headers.service import VBANServiceHeader, ServiceType
from aiovban.packet.body import Utf8StringBody

class TestChatStream(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.device = VBANDevice(address="127.0.0.1", _client=self.mock_client)

    async def test_chat_stream_creation(self):
        stream = await self.device.chat_stream("TestChat")
        self.assertIsInstance(stream, VBANChatStream)
        self.assertEqual(stream.name, "TestChat")
        self.assertIn("TestChat", self.device._streams)

    async def test_send_chat(self):
        stream = await self.device.chat_stream("TestChat")
        with patch.object(stream, 'send_packet', return_value=None) as mock_send:
            await stream.send_chat("Hello World")
            
            mock_send.assert_called_once()
            packet = mock_send.call_args[0][0]
            self.assertIsInstance(packet.header, VBANServiceHeader)
            self.assertEqual(packet.header.service, ServiceType.Chat_UTF8)
            self.assertEqual(packet.header.streamname, "TestChat")
            self.assertEqual(packet.body.text, "Hello World\0")

    async def test_receive_chat(self):
        stream = await self.device.chat_stream("TestChat")
        header = VBANServiceHeader(service=ServiceType.Chat_UTF8, streamname="TestChat")
        body = Utf8StringBody("Incoming Message\0")
        packet = VBANPacket(header, body)

        # Simulate receiving the packet
        await self.device.handle_packet("127.0.0.1", packet)

        received_text = await stream.get_chat()
        self.assertEqual(received_text, "Incoming Message")

    async def test_default_routing(self):
        # Even if we didn't register a stream with a specific name, 
        # VBANDevice should route to "VBAN Chat" by default for ServiceType.Chat_UTF8
        default_stream = await self.device.chat_stream("VBAN Chat")
        
        header = VBANServiceHeader(service=ServiceType.Chat_UTF8, streamname="RandomStreamName")
        body = Utf8StringBody("Default Route Message\0")
        packet = VBANPacket(header, body)

        await self.device.handle_packet("127.0.0.1", packet)

        received_text = await default_stream.get_chat()
        self.assertEqual(received_text, "Default Route Message")

if __name__ == "__main__":
    unittest.main()
