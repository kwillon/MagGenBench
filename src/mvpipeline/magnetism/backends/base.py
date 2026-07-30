from __future__ import annotations

from typing import Protocol

from ..schema import MagnetismInput, MagnetismResult


class MagnetismBackend(Protocol):
    name: str
    model_name: str
    moment_unit: str
    moment_normalization: str

    def predict(self, item: MagnetismInput) -> MagnetismResult:
        """Return a structured magnetic prediction result."""
