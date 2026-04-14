from dataclasses import dataclass
from typing import TYPE_CHECKING

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

    async def set_gain(self, value: float):
        """Set gain in dB (-60.0 to +12.0)."""
        value = max(-60.0, min(12.0, value))
        await self.remote.send_command(f"{self.identifier}.Gain={value:.1f};")

    async def set_mute(self, value: bool):
        """Set mute state."""
        await self.remote.send_command(f"{self.identifier}.Mute={1 if value else 0};")

    async def set_mono(self, value: bool):
        """Set mono state."""
        await self.remote.send_command(f"{self.identifier}.Mono={1 if value else 0};")

    async def set_label(self, value: str):
        """Set the label."""
        await self.remote.send_command(f'{self.identifier}.Label="{value}";')
