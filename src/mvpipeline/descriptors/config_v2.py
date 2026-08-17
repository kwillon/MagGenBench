from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..magnetism.config import MagneticElementGroups, load_magnetism_config
from .schema_v2 import DESCRIPTOR_V2_SCHEMA_VERSION


@dataclass(frozen=True)
class MagneticDescriptorV2RuntimeConfig:
    schema_version: str
    symprec: float
    angle_tolerance: float
    local_geometry_method: str
    local_geometry_cutoff: float
    local_geometry_tolerance: float
    local_geometry_get_all_sites: bool
    local_geometry_use_weights: bool
    preserve_input_order: bool
    require_unique_sample_uid: bool
    pre_round_floats: bool
    magnetic_elements: MagneticElementGroups

    @property
    def configured_magnetic_elements(self) -> frozenset[str]:
        return self.magnetic_elements.all_elements


def _read_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_magnetic_descriptor_v2_runtime_config(
    descriptor_config_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> MagneticDescriptorV2RuntimeConfig:
    descriptor_path = Path(descriptor_config_path).resolve()
    descriptor_data = _read_yaml(descriptor_path)

    config = descriptor_data.get("descriptors_v2_magnetic")
    if not isinstance(config, dict):
        raise ValueError("Missing descriptors_v2_magnetic mapping")

    schema_version = str(config.get("schema_version", ""))
    if schema_version != DESCRIPTOR_V2_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Descriptor v2 schema version: {schema_version}"
        )

    symmetry = config.get("symmetry")
    local_geometry = config.get("local_geometry")
    output = config.get("output")

    if not isinstance(symmetry, dict):
        raise ValueError("Missing descriptors_v2_magnetic.symmetry mapping")
    if not isinstance(local_geometry, dict):
        raise ValueError(
            "Missing descriptors_v2_magnetic.local_geometry mapping"
        )
    if not isinstance(output, dict):
        raise ValueError("Missing descriptors_v2_magnetic.output mapping")

    method = str(local_geometry.get("method", ""))
    if method != "MinimumDistanceNN":
        raise ValueError(f"Unsupported local geometry method: {method}")

    use_weights = bool(local_geometry.get("use_weights", False))
    if use_weights:
        raise ValueError("Descriptor v2 requires use_weights=false")

    magnetic_config_value = config.get("magnetic_screening_config")
    if not magnetic_config_value:
        raise ValueError(
            "Missing descriptors_v2_magnetic.magnetic_screening_config"
        )

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else descriptor_path.parent.parent
    )
    magnetic_path = Path(str(magnetic_config_value))
    if not magnetic_path.is_absolute():
        magnetic_path = root / magnetic_path

    magnetism_config = load_magnetism_config(magnetic_path)
    if not magnetism_config.magnetic_elements.all_elements:
        raise ValueError("Configured magnetic element set is empty")

    return MagneticDescriptorV2RuntimeConfig(
        schema_version=schema_version,
        symprec=float(symmetry["symprec"]),
        angle_tolerance=float(symmetry["angle_tolerance"]),
        local_geometry_method=method,
        local_geometry_cutoff=float(local_geometry["cutoff_angstrom"]),
        local_geometry_tolerance=float(local_geometry["tolerance"]),
        local_geometry_get_all_sites=bool(local_geometry["get_all_sites"]),
        local_geometry_use_weights=use_weights,
        preserve_input_order=bool(output["preserve_input_order"]),
        require_unique_sample_uid=bool(output["require_unique_sample_uid"]),
        pre_round_floats=bool(output["pre_round_floats"]),
        magnetic_elements=magnetism_config.magnetic_elements,
    )
