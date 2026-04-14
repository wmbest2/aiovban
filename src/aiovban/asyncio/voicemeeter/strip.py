from dataclasses import dataclass
from .base import VoicemeeterBase

@dataclass
class VoicemeeterStrip(VoicemeeterBase):
    solo: bool = False
    compressor: float = 0.0
    gate: float = 0.0
    denoiser: float = 0.0
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

    async def set_compressor(self, value: float):
        """Set compressor knob (0.0 to 10.0)."""
        value = max(0.0, min(10.0, value))
        await self.remote.send_command(f"{self.identifier}.Comp={value:.1f};")

    async def set_gate(self, value: float):
        """Set gate knob (0.0 to 10.0)."""
        value = max(0.0, min(10.0, value))
        await self.remote.send_command(f"{self.identifier}.Gate={value:.1f};")

    async def set_denoiser(self, value: float):
        """Set denoiser knob (0.0 to 10.0)."""
        value = max(0.0, min(10.0, value))
        await self.remote.send_command(f"{self.identifier}.Denoiser={value:.1f};")

    async def set_bus_routing(self, bus: str, value: bool):
        """Set routing to A1, B1, etc."""
        target = bus.upper()
        await self.remote.send_command(f"{self.identifier}.{target}={1 if value else 0};")
