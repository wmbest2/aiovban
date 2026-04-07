import logging
import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict

from .device import VBANDevice
from ..enums import State, VBANBaudRate, VoicemeeterType
from ..packet import VBANPacket
from ..packet.body import Utf8StringBody
from ..packet.body.service.rt_packets import RTPacketBodyType0
from ..packet.headers.text import VBANTextHeader, VBANTextStreamType

logger = logging.getLogger(__package__)

@dataclass
class VoicemeeterBase:
    index: int
    remote: 'VoicemeeterRemote'
    label: str = ""
    gain: float = 0.0
    mute: bool = False
    is_virtual: bool = False

    @property
    def identifier(self) -> str:
        raise NotImplementedError

    async def set_gain(self, value: float):
        """Set gain in dB (-60.0 to +12.0)."""
        value = max(-60.0, min(12.0, value))
        await self.remote.send_command(f"{self.identifier}.Gain={value:.1f};")

    async def set_mute(self, value: bool):
        """Set mute state."""
        await self.remote.send_command(f"{self.identifier}.Mute={1 if value else 0};")

    async def set_label(self, value: str):
        """Set the label."""
        await self.remote.send_command(f'{self.identifier}.Label="{value}";')

class VoicemeeterStrip(VoicemeeterBase):
    solo: bool = False
    a1: bool = False
    a2: bool = False
    a3: bool = False
    b1: bool = False
    b2: bool = False
    b3: bool = False

    @property
    def identifier(self) -> str:
        return f"Strip[{self.index}]"

    async def set_solo(self, value: bool):
        await self.remote.send_command(f"{self.identifier}.Solo={1 if value else 0};")

    async def set_bus_routing(self, bus: str, value: bool):
        """Set routing to A1, B1, etc."""
        target = bus.upper()
        await self.remote.send_command(f"{self.identifier}.{target}={1 if value else 0};")

class VoicemeeterBus(VoicemeeterBase):
    @property
    def identifier(self) -> str:
        return f"Bus[{self.index}]"

class VoicemeeterRemote:
    """High-level abstraction for controlling VoiceMeeter via VBAN."""

    def __init__(self, device: VBANDevice, command_stream: str = "Command1", offline_timeout: float = 5.0):
        self.device = device
        self.command_stream_name = command_stream
        self.offline_timeout = offline_timeout
        
        # Internal storage for all possible 8 strips/buses
        self._all_strips = [VoicemeeterStrip(i, self) for i in range(8)]
        self._all_buses = [VoicemeeterBus(i, self) for i in range(8)]
        
        self.type: Optional[VoicemeeterType] = None
        self.version: str = "Unknown"
        self.last_update: float = 0
        
        self._cmd_framecount = 0
        self._callbacks: List[Callable[['VoicemeeterRemote'], None]] = []
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def online(self) -> bool:
        """Check if we have received an RT packet recently."""
        if self.last_update == 0:
            return False
        return (time.time() - self.last_update) < self.offline_timeout

    @property
    def strips(self) -> List[VoicemeeterStrip]:
        """Get the list of active input strips for the discovered type."""
        if not self.type:
            return []
        phys = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5
        virt = 1 if self.type == VoicemeeterType.VOICEMEETER else 2 if self.type == VoicemeeterType.BANANA else 3
        return self._all_strips[:phys + virt]

    @property
    def buses(self) -> List[VoicemeeterBus]:
        """Get the list of active output buses for the discovered type."""
        if not self.type:
            return []
        phys = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5
        virt = 0 if self.type == VoicemeeterType.VOICEMEETER else 2 if self.type == VoicemeeterType.BANANA else 3
        return self._all_buses[:phys + virt]

    async def start(self):
        """Start the background worker to drain RT packets."""
        if self._worker_task:
            return
        
        # Ensure we have an RT stream registered
        rt_stream = self.device._streams.get("Voicemeeter-RTP")
        if not rt_stream:
            # Try to register a default one if not present
            rt_stream = await self.device.rt_stream(update_interval=0xFF)
            
        self._worker_task = asyncio.create_task(self._worker(rt_stream))
        logger.info(f"VoicemeeterRemote worker started for {self.device.address}")

    async def stop(self):
        """Stop the background worker and close the RT stream."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            
        rt_stream = self.device._streams.get("Voicemeeter-RTP")
        if rt_stream and hasattr(rt_stream, "close"):
            await rt_stream.close()

    async def _worker(self, stream):
        """Background loop to consume RT packets."""
        while True:
            try:
                packet = await stream.get_packet()
                if isinstance(packet.body, RTPacketBodyType0):
                    self.apply_rt_packet(packet.body)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in VoicemeeterRemote worker: {e}")
                await asyncio.sleep(1)

    def add_callback(self, callback: Callable[['VoicemeeterRemote', RTPacketBodyType0], None]):
        """Add a callback to be notified when state updates arrive."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[['VoicemeeterRemote', RTPacketBodyType0], None]):
        self._callbacks.remove(callback)

    async def restart(self):
        """Restart the VoiceMeeter audio engine."""
        await self.send_command("Command.Restart=1;")

    async def show(self):
        """Show the VoiceMeeter window."""
        await self.send_command("Command.Show=1;")

    async def lock(self, value: bool):
        """Lock or unlock the VoiceMeeter GUI."""
        await self.send_command(f"Command.Lock={1 if value else 0};")

    async def send_command(self, cmd: str):
        """Send a raw text command to VoiceMeeter."""
        header = VBANTextHeader(
            baud=VBANBaudRate.RATE_256000,
            streamname=self.command_stream_name,
            stream_type=VBANTextStreamType.UTF_8
        )
        self._cmd_framecount += 1
        header.framecount = self._cmd_framecount
        packet = VBANPacket(header, Utf8StringBody(cmd + "\0"))
        self.device._client.send_datagram(packet.pack(), (self.device.address, self.device.default_port))
        logger.debug(f"Voicemeeter command sent: {cmd}")

    def apply_rt_packet(self, body: RTPacketBodyType0):
        """Update internal state from an RT packet and notify callbacks."""
        self.type = body.voice_meeter_type
        self.version = body.voice_meeter_version
        self.last_update = time.time()
        
        phys_in = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5
        phys_out = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5

        for i, strip_data in enumerate(body.strips):
            if i < len(self._all_strips):
                strip = self._all_strips[i]
                strip.label = strip_data.label
                strip.mute = bool(strip_data.state & State.MODE_MUTE)
                strip.solo = bool(strip_data.state & State.MODE_SOLO)
                strip.gain = strip_data.layers[0] / 100.0
                strip.is_virtual = (i >= phys_in)
                strip.a1 = bool(strip_data.state & State.MODE_BUSA1)
                strip.a2 = bool(strip_data.state & State.MODE_BUSA2)
                strip.a3 = bool(strip_data.state & State.MODE_BUSA3)
                strip.b1 = bool(strip_data.state & State.MODE_BUSB1)
                strip.b2 = bool(strip_data.state & State.MODE_BUSB2)
                strip.b3 = bool(strip_data.state & State.MODE_BUSB3)

        for i, bus_data in enumerate(body.buses):
            if i < len(self._all_buses):
                bus = self._all_buses[i]
                bus.label = bus_data.label
                bus.mute = bool(bus_data.state & State.MODE_MUTE)
                bus.gain = bus_data.gain / 100.0
                bus.is_virtual = (i >= phys_out)

        for callback in self._callbacks:
            try:
                callback(self, body)
            except Exception as e:
                logger.error(f"Error in VoicemeeterRemote callback: {e}")
