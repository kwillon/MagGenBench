from __future__ import annotations

from typing import Mapping, Union

from ..config import MagnetismBackendSettings, backend_settings_from_mapping
from .base import MagnetismBackend
from .fake import FakeMagnetismBackend


BackendConfigLike = Union[str, Mapping[str, object], MagnetismBackendSettings]


def create_magnetism_backend(config: BackendConfigLike) -> MagnetismBackend:
    if isinstance(config, str):
        settings = MagnetismBackendSettings(name=config)
    elif isinstance(config, MagnetismBackendSettings):
        settings = config
    else:
        settings = backend_settings_from_mapping(config)

    name = settings.name.lower()
    if name == "fake":
        return FakeMagnetismBackend(model_name=settings.model_name)
    if name == "sklearn":
        from .sklearn import SklearnMagnetismBackend

        return SklearnMagnetismBackend(settings=settings)
    raise ValueError(f"Unsupported magnetism backend: {settings.name}")
