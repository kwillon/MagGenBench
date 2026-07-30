"""Magnetic property prediction contracts.

This package is separate from validation.magnetism, which remains elemental
screening only.
"""

from .schema import MagnetismInput, MagnetismResult, MagnetismStatus
from .uncertainty import confidence_from_uncertainty_proxy, risk_level_from_confidence

__all__ = [
    "MagnetismInput",
    "MagnetismResult",
    "MagnetismStatus",
    "confidence_from_uncertainty_proxy",
    "risk_level_from_confidence",
]
