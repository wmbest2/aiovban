from dataclasses import dataclass, field
from typing import Any

from .streams import VBANIncomingStream, VBANTextStream, VBANRTStream, VBANStream, VBANOutgoingStream
from ..enums import BackPressureStrategy
from ..packet import VBANPacket
from ..packet.body.service import DeviceType, Features
from ..packet.headers.service import PingFunctions, ServiceType, VBANServiceHeader


@dataclass
class VBANDevice:
    address: str
    port: int = 6980
    default_stream_size: int = 200

    _client: Any = None
    _streams: dict = field(default_factory=dict)

    async def handle_packet(self, address, packet: VBANPacket):
        stream: VBANStream = self._streams.get(packet.header.streamname)
        from ..packet.headers.service import VBANServiceHeader
        if stream and isinstance(stream, VBANIncomingStream):
            await stream.handle_packet(packet)
        elif packet.header.streamname == 'VBAN Service' and isinstance(packet.header, VBANServiceHeader):
            if packet.header.service == ServiceType.Identification and packet.header.function == PingFunctions.Request:
                print(f"Received ping request from {address}")
                await self.send_ping_response(address)

        else:
            print(f"Received packet for unregistered stream {packet.header.streamname} from {address}")
            print(packet.header)

    async def send_ping_response(self, address):
        from ..packet.body.service import Ping
        response_body = Ping(
                deviceType=DeviceType.Receptor,
                features=Features.Audio | Features.Text,
                deviceName='Python VBAN Client',
                version="1.0"
            )
        packet = VBANPacket(
            header=VBANServiceHeader(
                streamname='VBAN Service',
                service=ServiceType.Identification,
                function=PingFunctions.Response
            ),
            body=response_body.pack()
        )
        print(f"Sending ping response {response_body}")
        out_stream = VBANOutgoingStream(name="VBAN Service", _client=self._client)
        await out_stream.connect(address, self.port)
        await out_stream.send_packet(packet)

    def receive_stream(self, stream_name: str, back_pressure_strategy=BackPressureStrategy.DROP):
        stream = VBANIncomingStream(stream_name, queue_size=self.default_stream_size, _back_pressure_strategy=back_pressure_strategy)
        self._streams[stream_name] = stream
        return stream

    async def text_stream(self, stream_name: str):
        stream = VBANTextStream(stream_name, _client=self._client)
        await stream.connect(self.address, self.port)
        self._streams[stream_name] = stream
        return stream

    async def rt_stream(self, update_interval: int, automatic_renewal=True, back_pressure_strategy=BackPressureStrategy.DROP):
        stream = VBANRTStream(
            name = "VBAN-RTP",
            queue_size=20,
            automatic_renewal=automatic_renewal,
            update_interval=update_interval,
            _back_pressure_strategy=back_pressure_strategy,
            _client=self._client
        )

        await stream.connect(self.address, self.port)

        self._streams[stream.name] = stream
        self._streams['Voicemeeter-RTP'] = stream # Responses come to this stream
        return stream
