import logging
import asyncio
import time
from typing import Callable, List, Optional, Any, Dict
from enum import Enum

from ..device import VBANDevice
from ...enums import State, VBANBaudRate, VoicemeeterType, BusMode
from ...packet import VBANPacket
from ...packet.body import Utf8StringBody
from ...packet.body.service.rt_packets import RTPacketBodyType0
from ...packet.headers.text import VBANTextHeader, VBANTextStreamType

from .strip import VoicemeeterStrip
from .bus import VoicemeeterBus

logger = logging.getLogger(__package__)

class VoicemeeterRemote:
    """
    High-level abstraction for controlling VoiceMeeter via VBAN.
    
    IMPORTANT: This class follows a unidirectional state model. The attributes of the
    strips and buses (e.g., strip.mute, bus.gain) represent the actual state of the
    remote VoiceMeeter instance as reported via incoming RT packets.
    
    When a `set_` method is called, a command is sent to the remote instance, but the 
    local attribute is not updated immediately. The change will only be reflected 
    after the remote instance processes the command and sends back a new RT packet.
    There is a inherent delay (typically 20ms-500ms) between a command being sent 
    and the state updating in this object.
    """

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
        
        # Recorder state
        self.recorder_playing = False
        self.recorder_recording = False
        self.recorder_paused = False

        self._cmd_framecount = 0
        self._callbacks: List[Callable[['VoicemeeterRemote', RTPacketBodyType0], None]] = []
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
        
        rt_stream = self.device._streams.get("Voicemeeter-RTP")
        if not rt_stream:
            rt_stream = await self.device.rt_stream(update_interval=0xFF)
            
        self._worker_task = asyncio.create_task(self._worker(rt_stream))
        logger.info(f"VoicemeeterRemote worker started for {self.device.address}")

    async def stop(self):
        """Stop the background worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

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

    def _format_value(self, value: Any) -> str:
        """Internal helper to format a Python value for VoiceMeeter."""
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, float):
            return f"{value:.1f}"
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)

    async def set_parameter(self, path: str, value: Any):
        """Set a single parameter on the remote VoiceMeeter instance."""
        formatted = self._format_value(value)
        await self.send_command(f"{path}={formatted};")

    async def set_parameters(self, params: Dict[str, Any]):
        """Set multiple parameters in a single VBAN packet."""
        commands = [f"{path}={self._format_value(val)};" for path, val in params.items()]
        await self.send_command("".join(commands))

    async def restart(self): 
        """Restart the audio engine."""
        await self.set_parameter("Command.Restart", 1)
        
    async def show(self): 
        """Show the VoiceMeeter window."""
        await self.set_parameter("Command.Show", 1)
        
    async def lock(self, value: bool): 
        """Lock or unlock the VoiceMeeter GUI."""
        await self.set_parameter("Command.Lock", value)

    async def set_recorder_play(self, value: bool): 
        """Start or stop playback."""
        await self.set_parameter("Recorder.play", value)
        
    async def set_recorder_stop(self, value: bool): 
        """Stop the recorder/player."""
        if value: await self.set_parameter("Recorder.stop", 1)
        
    async def set_recorder_record(self, value: bool): 
        """Start or stop recording."""
        await self.set_parameter("Recorder.record", value)
        
    async def set_recorder_pause(self, value: bool): 
        """Toggle pause."""
        await self.set_parameter("Recorder.pause", value)

    async def send_command(self, cmd: str):
        """Send a raw text command string to VoiceMeeter."""
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
        
        self.recorder_playing = bool(body.transport_bits & 0x01)
        self.recorder_recording = bool(body.transport_bits & 0x02)
        self.recorder_paused = bool(body.transport_bits & 0x08)

        phys_in = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5
        phys_out = 2 if self.type == VoicemeeterType.VOICEMEETER else 3 if self.type == VoicemeeterType.BANANA else 5

        input_offset = 0
        for i, strip_data in enumerate(body.strips):
            if i < len(self._all_strips):
                strip = self._all_strips[i]
                strip.label = strip_data.label
                strip.mute = bool(strip_data.state & State.MODE_MUTE)
                strip.solo = bool(strip_data.state & State.MODE_SOLO)
                strip.mono = bool(strip_data.state & State.MODE_MONO)
                strip.mc = bool(strip_data.state & State.MODE_MUTEC)
                strip.gain = strip_data.layers[0] / 100.0
                strip.is_virtual = (i >= phys_in)
                
                ch_count = 2 if not strip.is_virtual else 8
                if input_offset + ch_count <= len(body.input_levels):
                    strip.levels = [lv / 100.0 for lv in body.input_levels[input_offset : input_offset + ch_count]]
                    input_offset += ch_count
                
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
                bus.mono = bool(bus_data.state & State.MODE_MONO)
                bus.eq = bool(bus_data.state & State.MODE_EQ)
                bus.mode = BusMode((int(bus_data.state) & int(State.MODE_MASK)) >> 4)
                bus.gain = bus_data.gain / 100.0
                bus.is_virtual = (i >= phys_out)
                
                bus_offset = i * 8
                if bus_offset + 8 <= len(body.output_levels):
                    bus.levels = [lv / 100.0 for lv in body.output_levels[bus_offset : bus_offset + 8]]

        for callback in self._callbacks:
            try:
                callback(self, body)
            except Exception as e:
                logger.error(f"Error in VoicemeeterRemote callback: {e}")
