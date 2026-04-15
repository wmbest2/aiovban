from dataclasses import dataclass, field
from typing import List


@dataclass
class PEQBand:
    """One band of the 6-band parametric EQ."""
    enabled: bool = False
    type: int = 0       # filter type (Voicemeeter internal enum)
    gain: float = 0.0   # dB
    freq: float = 0.0   # Hz
    q: float = 0.0


@dataclass
class EQParams:
    """EQ parameters — shared between strips (Type 1) and buses (Type 2).

    ``low``, ``mid``, ``high`` are the simple 3-band gains (raw int16 from
    Voicemeeter). ``bands`` is the full 6-band parametric EQ.
    """
    low: int = 0
    mid: int = 0
    high: int = 0
    bands: List[PEQBand] = field(default_factory=list)


@dataclass
class CompressorParams:
    """Full compressor parameters from RT Type 1 (strips only)."""
    gain_in: int = 0
    attack: int = 0
    release: int = 0
    knee: int = 0
    ratio: int = 0
    threshold: int = 0
    enabled: bool = False
    auto: bool = False
    gain_out: int = 0


@dataclass
class GateParams:
    """Full gate/expander parameters from RT Type 1 (strips only)."""
    threshold: int = 0
    damping: int = 0
    sidechain: int = 0
    attack: int = 0
    hold: int = 0
    release: int = 0


@dataclass
class PitchParams:
    """Pitch shifter parameters from RT Type 1 (strips only)."""
    enabled: bool = False
    drywet: int = 0
    value: int = 0
    lo: int = 0
    med: int = 0
    high: int = 0
