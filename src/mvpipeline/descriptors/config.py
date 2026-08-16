from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import DESCRIPTOR_SCHEMA_VERSION


@dataclass(frozen=True)
class DescriptorRuntimeConfig:
    schema_version: str
    reference_pymatgen_version: str
    symprec: float
    angle_tolerance: float
    local_geometry_method: str
    local_geometry_cutoff: float
    local_geometry_tolerance: float
    local_geometry_get_all_sites: bool
    local_geometry_use_weights: bool
    magnetic_screening_elements: frozenset[str]


def _read_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_descriptor_runtime_config(
    descriptor_config_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> DescriptorRuntimeConfig:
    descriptor_path = Path(descriptor_config_path).resolve()
    descriptor_data = _read_yaml(descriptor_path)

    config = descriptor_data.get("descriptors")
    if not isinstance(config, dict):
        raise ValueError("Missing descriptors mapping")

    schema_version = str(config.get("schema_version", ""))
    if schema_version != DESCRIPTOR_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported descriptor schema version: {schema_version}"
        )

    symmetry = config.get("symmetry")
    local_geometry = config.get("local_geometry")
    composition = config.get("composition")

    if not isinstance(symmetry, dict):
        raise ValueError("Missing descriptors.symmetry mapping")
    if not isinstance(local_geometry, dict):
        raise ValueError("Missing descriptors.local_geometry mapping")
    if not isinstance(composition, dict):
        raise ValueError("Missing descriptors.composition mapping")

    method = str(local_geometry.get("method", ""))
    if method != "MinimumDistanceNN":
        raise ValueError(
            f"Unsupported local geometry method: {method}"
        )

    use_weights = bool(local_geometry.get("use_weights", False))
    if use_weights:
        raise ValueError(
            "Descriptor v1 requires local_geometry.use_weights=false"
        )

    magnetic_config_value = composition.get(
        "magnetic_screening_config"
    )
    if not magnetic_config_value:
        raise ValueError(
            "Missing descriptors.composition.magnetic_screening_config"
        )

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else descriptor_path.parent.parent
    )
    magnetic_path = Path(str(magnetic_config_value))
    if not magnetic_path.is_absolute():
        magnetic_path = root / magnetic_path
    magnetic_path = magnetic_path.resolve()

    magnetic_data = _read_yaml(magnetic_path)
    magnetism = magnetic_data.get("magnetism")
    if not isinstance(magnetism, dict):
        raise ValueError("Missing magnetism mapping")

    magnetic_groups = magnetism.get("magnetic_elements")
    if not isinstance(magnetic_groups, dict):
        raise ValueError("Missing magnetism.magnetic_elements mapping")

    magnetic_elements: set[str] = set()
    for group_name, group_values in magnetic_groups.items():
        if not isinstance(group_values, list):
            raise ValueError(
                f"Magnetic element group must be a list: {group_name}"
            )
        magnetic_elements.update(str(value) for value in group_values)

    if not magnetic_elements:
        raise ValueError("Magnetic screening element set is empty")

    return DescriptorRuntimeConfig(
        schema_version=schema_version,
        reference_pymatgen_version=str(
            config.get("reference_pymatgen_version", "")
        ),
        symprec=float(symmetry["symprec"]),
        angle_tolerance=float(symmetry["angle_tolerance"]),
        local_geometry_method=method,
        local_geometry_cutoff=float(
            local_geometry["cutoff_angstrom"]
        ),
        local_geometry_tolerance=float(
            local_geometry["tolerance"]
        ),
        local_geometry_get_all_sites=bool(
            local_geometry["get_all_sites"]
        ),
        local_geometry_use_weights=use_weights,
        magnetic_screening_elements=frozenset(magnetic_elements),
    )
