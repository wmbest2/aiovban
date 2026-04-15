from dataclasses import dataclass, field
from .base import VoicemeeterBase
from ...enums import BusMode, State
from .params import EQParams

@dataclass
class VoicemeeterBus(VoicemeeterBase):
    mode: BusMode = BusMode.NORMAL
    levels: list[float] = field(default_factory=list)
    state: State = State(0)
    eq: bool = False
    solo: bool = False

    # Expanded parameters from RT Type 2
    eq_params: EQParams = field(default_factory=EQParams)

    @property
    def identifier(self) -> str:
        return f"Bus[{self.index}]"

    async def set_mode(self, value: BusMode):
        """Set the bus mode."""
        await self._set_param("Mode", value)

    async def set_eq(self, value: bool):
        """Set EQ state."""
        await self._set_param("EQ", value)

    async def set_solo(self, value: bool):
        """Set solo state."""
        await self._set_param("Solo", value)
