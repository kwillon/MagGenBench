from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class EnergyStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class EnergyInput:
    """Minimal input contract for an energy-stage structure."""

    structure_id: str
    structure: Any
    n_atoms: int
    composition: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EnergyResult:
    """Serializable energy-stage result.

    Values named ``formation_energy_proxy_*`` are isolated-atom-reference
    proxies. They are not true formation energies and not energy above hull.
    """

    structure_id: str
    status: EnergyStatus
    error_code: str = ""
    error_message: str = ""
    backend: str = ""
    model_name: str = ""
    energy_unit: str = "eV"
    total_energy_eV: Optional[float] = None
    total_energy_eV_per_atom: Optional[float] = None
    formation_energy_proxy_eV: Optional[float] = None
    formation_energy_proxy_eV_per_atom: Optional[float] = None
    stability_energy_proxy_eV_per_atom: Optional[float] = None
    details: Mapping[str, Any] = field(default_factory=dict)
