from dataclasses import dataclass, field
from typing import Any

from .streams import VBANIncomingStream, VBANTextStream, VBANCommandStream, VBANStream
from ..packet import VBANPacket


@dataclass
class VBANDevice:
    address: str
    port: int = 6980
    default_stream_size: int = 200

    _client: Any = None
    _streams: dict = field(default_factory=dict)

    async def handle_packet(self, packet: VBANPacket):
        stream: VBANStream = self._streams.get(packet.header.streamname)
        if stream and isinstance(stream, VBANIncomingStream):
            await stream.handle_packet(packet)

    def receive_stream(self, stream_name: str):
        stream = VBANIncomingStream(stream_name, queue_size=self.default_stream_size)
        self._streams[stream_name] = stream
        return stream

    def text_stream(self, stream_name: str):
        stream = VBANTextStream(stream_name, _client=self._client)
        self._streams[stream_name] = stream
        return stream

    async def command_stream(self, update_interval: int, stream_name: str):
        stream = VBANCommandStream(stream_name, queue_size=self.default_stream_size, update_interval=update_interval, _client=self._client)

        await stream.connect(self.address, self.port)

        self._streams[stream_name] = stream
        return stream
