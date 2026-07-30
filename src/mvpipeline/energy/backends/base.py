from __future__ import annotations

from typing import Protocol

from ..schema import EnergyInput, EnergyResult


class EnergyBackend(Protocol):
    name: str
    model_name: str

    def predict(self, item: EnergyInput) -> EnergyResult:
        """Return a structured energy result instead of raising user-facing errors."""
