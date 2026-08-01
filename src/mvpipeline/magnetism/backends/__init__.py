"""Magnetism backend interfaces and lightweight backends."""

from .base import MagnetismBackend
from .factory import create_magnetism_backend
from .fake import FakeMagnetismBackend
from .sklearn import SklearnMagnetismBackend

__all__ = [
    "MagnetismBackend",
    "FakeMagnetismBackend",
    "SklearnMagnetismBackend",
    "create_magnetism_backend",
]
