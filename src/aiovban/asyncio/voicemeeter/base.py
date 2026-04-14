from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .remote import VoicemeeterRemote

@dataclass
class VoicemeeterBase:
    index: int
    remote: 'VoicemeeterRemote'
    label: str = ""
    gain: float = 0.0
    mute: bool = False
    mono: bool = False
    is_virtual: bool = False

    @property
    def identifier(self) -> str:
        raise NotImplementedError

    async def _set_param(self, param: str, value: Any):
        """Internal helper to set a parameter on this strip/bus."""
        await self.remote.set_parameter(f"{self.identifier}.{param}", value)

    async def set_gain(self, value: float):
        """Set gain in dB (-60.0 to +12.0)."""
        await self._set_param("Gain", max(-60.0, min(12.0, value)))

    async def set_mute(self, value: bool):
        """Set mute state."""
        await self._set_param("Mute", value)

    async def set_mono(self, value: bool):
        """Set mono state."""
        await self._set_param("Mono", value)

    async def set_label(self, value: str):
        """Set the label."""
        await self._set_param("Label", value)
