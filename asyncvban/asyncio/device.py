from dataclasses import dataclass, field
from typing import Any

from .streams import VBANIncomingStream, VBANTextStream, VBANCommandStream, VBANStream
from ..enums import BackPressureStrategy
from ..packet import VBANPacket


@dataclass
class VBANDevice:
    address: str
    port: int = 6980
    default_stream_size: int = 200

    _client: Any = None
    _streams: dict = field(default_factory=dict)

    async def handle_packet(self, address, packet: VBANPacket):
        stream: VBANStream = self._streams.get(packet.header.streamname)
        if stream and isinstance(stream, VBANIncomingStream):
            await stream.handle_packet(packet)
        else:
            print(f"Received packet for unregistered stream {packet.header.streamname} from {address}")
            print(packet.header)

    def receive_stream(self, stream_name: str, back_pressure_strategy=BackPressureStrategy.DROP):
        stream = VBANIncomingStream(stream_name, queue_size=self.default_stream_size, _back_pressure_strategy=back_pressure_strategy)
        self._streams[stream_name] = stream
        return stream

    def text_stream(self, stream_name: str):
        stream = VBANTextStream(stream_name, _client=self._client)
        self._streams[stream_name] = stream
        return stream

    async def command_stream(self, update_interval: int, stream_name: str, back_pressure_strategy=BackPressureStrategy.DROP):
        stream = VBANCommandStream(
            name = stream_name,
            queue_size=20,
            update_interval=update_interval,
            _back_pressure_strategy=back_pressure_strategy,
            _client=self._client
        )

        await stream.connect(self.address, self.port)

        self._streams[stream_name] = stream
        self._streams['Voicemeeter-RTP'] = stream # Responses come to this stream
        return stream
