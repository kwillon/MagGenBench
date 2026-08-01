from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


class ReferenceEnergyProvider(Protocol):
    def get_reference_energy_eV(self, element_symbol: str) -> float:
        """Return reference energy for one atom of an element in eV."""


@dataclass
class DictReferenceEnergyProvider:
    values: Mapping[str, float] = field(default_factory=dict)

    def get_reference_energy_eV(self, element_symbol: str) -> float:
        return float(self.values[element_symbol])
