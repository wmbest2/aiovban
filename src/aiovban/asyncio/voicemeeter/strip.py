from dataclasses import dataclass, field
from typing import Any
from .base import VoicemeeterBase
from ...enums import State
from .params import EQParams, CompressorParams, GateParams, PitchParams, PEQBand

@dataclass
class VoicemeeterStrip(VoicemeeterBase):
    solo: bool = False
    eq: bool = False
    compressor: float = 0.0
    gate: float = 0.0
    denoiser: float = 0.0
    levels: list[float] = field(default_factory=list)
    state: State = State(0)
    mc: bool = False
    a1: bool = False
    a2: bool = False
    a3: bool = False
    a4: bool = False
    a5: bool = False
    b1: bool = False
    b2: bool = False
    b3: bool = False

    # Expanded parameters from RT Type 1
    eq_params: EQParams = field(default_factory=EQParams)
    comp_params: CompressorParams = field(default_factory=CompressorParams)
    gate_params: GateParams = field(default_factory=GateParams)
    pitch_params: PitchParams = field(default_factory=PitchParams)

    @property
    def identifier(self) -> str:
        return f"Strip[{self.index}]"

    async def set_solo(self, value: bool):
        await self._set_param("Solo", value)

    async def set_eq(self, value: bool):
        """Set EQ state."""
        await self._set_param("EQ", value)

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

    # Simple 3-band EQ
    async def set_eq_low(self, value: float):
        """Set simple EQ Low gain (-12.0 to 12.0)."""
        await self._set_param("EqGain1", max(-12.0, min(12.0, value)))

    async def set_eq_mid(self, value: float):
        """Set simple EQ Mid gain (-12.0 to 12.0)."""
        await self._set_param("EqGain2", max(-12.0, min(12.0, value)))

    async def set_eq_high(self, value: float):
        """Set simple EQ High gain (-12.0 to 12.0)."""
        await self._set_param("EqGain3", max(-12.0, min(12.0, value)))

    # Generic complex parameter setters
    async def set_comp_param(self, name: str, value: Any):
        """Set a compressor parameter (e.g., 'Threshold', 'Attack', 'Ratio')."""
        await self._set_param(f"Comp.{name}", value)

    async def set_gate_param(self, name: str, value: Any):
        """Set a gate parameter (e.g., 'Threshold', 'Attack', 'Release')."""
        await self._set_param(f"Gate.{name}", value)

    async def set_pitch_param(self, name: str, value: Any):
        """Set a pitch shifter parameter (e.g., 'DryWet', 'Value')."""
        await self._set_param(f"Pitch.{name}", value)

    async def set_eq_band_param(self, band: int, name: str, value: Any):
        """Set a 6-band PEQ parameter (band 1-6)."""
        await self._set_param(f"EQ.Band[{band-1}].{name}", value)
