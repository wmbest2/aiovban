from dataclasses import dataclass
from .base import VoicemeeterBase
from ...enums import BusMode

@dataclass
class VoicemeeterBus(VoicemeeterBase):
    mode: BusMode = BusMode.NORMAL

    @property
    def identifier(self) -> str:
        return f"Bus[{self.index}]"

    async def set_mode(self, value: BusMode):
        """Set the bus mode."""
        await self.remote.send_command(f"{self.identifier}.Mode={value.value};")
