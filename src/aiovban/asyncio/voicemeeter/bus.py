from dataclasses import dataclass, field
from .base import VoicemeeterBase
from ...enums import BusMode

@dataclass
class VoicemeeterBus(VoicemeeterBase):
    mode: BusMode = BusMode.NORMAL
    levels: list[float] = field(default_factory=list)
    eq: bool = False

    @property
    def identifier(self) -> str:
        return f"Bus[{self.index}]"

    async def set_mode(self, value: BusMode):
        """Set the bus mode."""
        await self._set_param("Mode", value)

    async def set_eq(self, value: bool):
        """Set EQ state."""
        await self._set_param("EQ", value)
