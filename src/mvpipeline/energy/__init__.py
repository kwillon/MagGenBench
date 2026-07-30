"""Energy-stage contracts and lightweight helpers.

This package intentionally avoids importing heavy ML backends at import time.
Real MatGL/CHGNet adapters belong behind optional, lazy imports in later phases.
"""

from .formation import formation_energy_proxy, formation_energy_proxy_per_atom
from .proxies import positive_formation_energy_proxy
from .schema import EnergyInput, EnergyResult, EnergyStatus

__all__ = [
    "EnergyInput",
    "EnergyResult",
    "EnergyStatus",
    "formation_energy_proxy",
    "formation_energy_proxy_per_atom",
    "positive_formation_energy_proxy",
]
