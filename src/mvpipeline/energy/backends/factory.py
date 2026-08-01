from __future__ import annotations

from typing import Mapping, Union

from ..config import EnergyBackendSettings, backend_settings_from_mapping
from .base import EnergyBackend
from .fake import FakeEnergyBackend


BackendConfigLike = Union[str, Mapping[str, object], EnergyBackendSettings]


def create_energy_backend(config: BackendConfigLike) -> EnergyBackend:
    if isinstance(config, str):
        settings = EnergyBackendSettings(name=config)
    elif isinstance(config, EnergyBackendSettings):
        settings = config
    else:
        settings = backend_settings_from_mapping(config)

    name = settings.name.lower()
    if name == "fake":
        return FakeEnergyBackend(model_name=settings.model_name)
    if name == "matgl":
        from .matgl import MatGLBackend

        return MatGLBackend(
            model_name=settings.model_name,
            device=settings.device,
            output_semantics=settings.output_semantics,
        )
    if name == "chgnet":
        from .chgnet import CHGNetBackend

        return CHGNetBackend(
            model_name=settings.model_name,
            model_selector=settings.model_selector,
            device=settings.device,
            output_semantics=settings.output_semantics,
        )
    raise ValueError(f"Unsupported energy backend: {settings.name}")
