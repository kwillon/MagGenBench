"""Magnetism backend interfaces and lightweight test backends."""

from .base import MagnetismBackend
from .fake import FakeMagnetismBackend

__all__ = ["MagnetismBackend", "FakeMagnetismBackend"]
