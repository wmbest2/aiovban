import logging
from dataclasses import dataclass, field
from typing import Any

from .streams import (
    VBANIncomingStream,
    VBANTextStream,
    VBANRTStream,
    VBANStream,
    BufferedVBANOutgoingStream,
)
from .util import BackPressureStrategy
from ..enums import VBANBaudRate
from ..packet import VBANPacket
from ..packet.body.service import Ping
from ..packet.headers.service import PingFunctions, ServiceType

logger = logging.getLogger(__package__)


@dataclass
class VBANDevice:
    address: str
    default_port: int = 6980
    default_stream_size: int = 100
    connected_application_data: Ping = None

    _client: Any = None
    _streams: dict = field(default_factory=dict)

    async def handle_packet(self, address, packet: VBANPacket):
        stream: VBANStream = self._streams.get(packet.header.streamname)
        from ..packet.headers.service import VBANServiceHeader

        if stream and isinstance(stream, VBANIncomingStream):
            await stream.handle_packet(packet)
        elif packet.header.streamname == "VBAN Service" and isinstance(
            packet.header, VBANServiceHeader
        ):
            if (
                packet.header.service == ServiceType.Identification
                and packet.header.function
                in [PingFunctions.Request, PingFunctions.Response]
            ):
                body: Ping = packet.body
                self.connected_application_data = body

        else:
            logger.debug(
                f"Received packet for unregistered stream {packet.header.streamname} from {address}"
            )
            logger.debug(packet.header)

    def receive_stream(
        self, stream_name: str, back_pressure_strategy=BackPressureStrategy.DROP
    ):
        stream = VBANIncomingStream(
            stream_name,
            queue_size=self.default_stream_size,
            back_pressure_strategy=back_pressure_strategy,
        )
        self._streams[stream_name] = stream
        return stream

    async def send_stream(
        self,
        stream_name: str,
        port: int = None,
        back_pressure_strategy=BackPressureStrategy.DROP,
    ):
        port = port or self.default_port
        stream = BufferedVBANOutgoingStream(
            stream_name,
            _client=self._client,
            back_pressure_strategy=back_pressure_strategy,
        )
        await stream.connect(self.address, port)
        self._streams[stream_name] = stream
        return stream

    async def text_stream(
        self,
        stream_name: str,
        baud_rate: VBANBaudRate = VBANBaudRate.RATE_256000,
        port: int = None,
    ):
        port = port or self.default_port
        stream = VBANTextStream(stream_name, _client=self._client, baud_rate=baud_rate)
        await stream.connect(self.address, port)
        self._streams[stream_name] = stream
        return stream

    async def rt_stream(
        self,
        update_interval: int,
        automatic_renewal=True,
        back_pressure_strategy=BackPressureStrategy.DROP,
    ):
        stream = VBANRTStream(
            name="VBAN-RTP",
            queue_size=100,
            automatic_renewal=automatic_renewal,
            update_interval=update_interval,
            back_pressure_strategy=back_pressure_strategy,
            _client=self._client,
        )

        await stream.connect(self.address, self.default_port)

        self._streams[stream.name] = stream
        self._streams["Voicemeeter-RTP"] = stream  # Responses come to this stream
        return stream
