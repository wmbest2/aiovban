from dataclasses import dataclass, field
from .base import VoicemeeterBase

@dataclass
class VoicemeeterStrip(VoicemeeterBase):
    solo: bool = False
    compressor: float = 0.0
    gate: float = 0.0
    denoiser: float = 0.0
    levels: list[float] = field(default_factory=list)
    mc: bool = False
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
        await self._set_param("Solo", value)

    async def set_compressor(self, value: float):
        """Set compressor knob (0.0 to 10.0)."""
        await self._set_param("Comp", max(0.0, min(10.0, value)))

    async def set_gate(self, value: float):
        """Set gate knob (0.0 to 10.0)."""
        await self._set_param("Gate", max(0.0, min(10.0, value)))

    async def set_denoiser(self, value: float):
        """Set denoiser knob (0.0 to 10.0)."""
        await self._set_param("Denoiser", max(0.0, min(10.0, value)))

    async def set_mc(self, value: bool):
        """Set Multi-Channel (MC) state."""
        await self._set_param("MC", value)

    async def set_bus_routing(self, bus: str, value: bool):
        """Set routing to A1, B1, etc."""
        await self._set_param(bus.upper(), value)
