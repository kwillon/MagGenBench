from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


VALID_DEVICES = {"auto", "cpu", "cuda"}
VALID_OUTPUT_SEMANTICS = {"total_energy_eV", "energy_per_atom_eV"}


@dataclass(frozen=True)
class EnergyBackendSettings:
    name: str = "fake"
    model_name: str = "deterministic-fake-v1"
    device: str = "cpu"
    output_semantics: str = "total_energy_eV"
    model_selector: str = "default"

    def __post_init__(self) -> None:
        if self.device not in VALID_DEVICES:
            raise ValueError(f"Unsupported energy device: {self.device}")
        if self.output_semantics not in VALID_OUTPUT_SEMANTICS:
            raise ValueError(
                f"Unsupported energy output semantics: {self.output_semantics}"
            )


@dataclass(frozen=True)
class EnergyConfig:
    backend: EnergyBackendSettings = EnergyBackendSettings()
    matgl: EnergyBackendSettings = EnergyBackendSettings(
        name="matgl",
        model_name="TensorNet-MatPES-PBE-v2025.1-PES",
        device="auto",
        output_semantics="total_energy_eV",
    )
    chgnet: EnergyBackendSettings = EnergyBackendSettings(
        name="chgnet",
        model_name="default",
        device="auto",
        output_semantics="energy_per_atom_eV",
        model_selector="default",
    )


def backend_settings_from_mapping(
    data: Mapping[str, Any], defaults: Optional[EnergyBackendSettings] = None
) -> EnergyBackendSettings:
    base = defaults or EnergyBackendSettings()
    return EnergyBackendSettings(
        name=str(data.get("name", base.name)),
        model_name=str(data.get("model_name", base.model_name)),
        device=str(data.get("device", base.device)),
        output_semantics=str(data.get("output_semantics", base.output_semantics)),
        model_selector=str(data.get("model_selector", base.model_selector)),
    )


def energy_config_from_mapping(data: Mapping[str, Any]) -> EnergyConfig:
    energy = data.get("energy", data) or {}
    default_cfg = EnergyConfig()
    return EnergyConfig(
        backend=backend_settings_from_mapping(
            energy.get("backend", {}) or {}, default_cfg.backend
        ),
        matgl=backend_settings_from_mapping(
            energy.get("matgl", {}) or {}, default_cfg.matgl
        ),
        chgnet=backend_settings_from_mapping(
            energy.get("chgnet", {}) or {}, default_cfg.chgnet
        ),
    )


def load_energy_config(path: str | Path) -> EnergyConfig:
    """Load energy config from YAML.

    PyYAML is imported only when this function is called.
    """

    import yaml

    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return energy_config_from_mapping(data)
