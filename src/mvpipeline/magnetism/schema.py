from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence


class MagnetismStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class MagnetismInput:
    """Minimal input contract for magnetic-moment prediction."""

    structure_id: str
    structure: Any
    composition: Mapping[str, float] = field(default_factory=dict)
    features: Optional[Sequence[float]] = None


@dataclass(frozen=True)
class MagnetismResult:
    """Serializable magnetic prediction result.

    The prediction is not magnetic ordering, saturation magnetization, Curie
    temperature, or a DFT magnetic moment unless a later backend proves that.
    """

    structure_id: str
    status: MagnetismStatus
    error_code: str = ""
    error_message: str = ""
    backend: str = ""
    model_name: str = ""
    predicted_moment_value: Optional[float] = None
    moment_unit: str = "unknown"
    moment_normalization: str = "unknown"
    uncertainty_proxy: Optional[float] = None
    confidence_score: Optional[float] = None
    risk_level: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)
