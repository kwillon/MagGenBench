"""Energy backend interfaces and lightweight test backends."""

from .base import EnergyBackend
from .fake import FakeEnergyBackend

__all__ = ["EnergyBackend", "FakeEnergyBackend"]
