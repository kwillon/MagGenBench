from __future__ import annotations

from typing import Any

from .schema import DescriptorResult


IDENTITY_FIELDS = [
    "sample_uid",
    "structure_id",
    "model_name",
    "model_short",
    "run_uid",
    "source_sample_id",
    "cif_path",
]

STRUCTURE_FIELDS = [
    "n_atoms",
    "lattice_a",
    "lattice_b",
    "lattice_c",
    "lattice_alpha",
    "lattice_beta",
    "lattice_gamma",
    "cell_volume",
    "volume_per_atom",
    "density",
    "min_lattice_length",
    "max_lattice_length",
    "lattice_length_ratio",
]

SYMMETRY_FIELDS = [
    "spacegroup_number",
    "spacegroup_symbol",
    "crystal_system",
    "point_group_symbol",
    "symmetry_status",
]

COMPOSITION_FIELDS = [
    "n_elements",
    "min_element_fraction",
    "max_element_fraction",
    "composition_entropy",
    "transition_metal_fraction",
    "d_block_fraction",
    "f_block_fraction",
    "lanthanide_fraction",
    "actinide_fraction",
    "magnetic_screening_element_fraction",
]

ELEMENT_PROPERTY_PREFIXES = [
    "atomic_number",
    "atomic_mass",
    "atomic_radius",
    "electronegativity",
    "periodic_row",
    "periodic_group",
]

ELEMENT_PROPERTY_SUFFIXES = [
    "mean",
    "min",
    "max",
    "range",
    "std",
    "coverage",
]

ELEMENT_PROPERTY_FIELDS = [
    f"{prefix}_{suffix}"
    for prefix in ELEMENT_PROPERTY_PREFIXES
    for suffix in ELEMENT_PROPERTY_SUFFIXES
]

LOCAL_GEOMETRY_FIELDS = [
    "nearest_neighbor_min",
    "nearest_neighbor_mean",
    "nearest_neighbor_std",
    "coordination_mean",
    "coordination_min",
    "coordination_max",
    "coordination_std",
    "local_geometry_status",
]

DESCRIPTOR_VALUE_FIELDS = [
    *STRUCTURE_FIELDS,
    *SYMMETRY_FIELDS,
    *COMPOSITION_FIELDS,
    *ELEMENT_PROPERTY_FIELDS,
    *LOCAL_GEOMETRY_FIELDS,
]

STATUS_FIELDS = [
    "descriptor_schema_version",
    "descriptor_v1_source",
    "descriptor_v1_status",
    "descriptor_v1_error_code",
    "descriptor_v1_error_message",
]

DESCRIPTOR_RECORD_FIELDS = [
    *IDENTITY_FIELDS,
    *DESCRIPTOR_VALUE_FIELDS,
    *STATUS_FIELDS,
]


def descriptor_result_to_record(result: DescriptorResult) -> dict[str, Any]:
    unknown = sorted(set(result.values) - set(DESCRIPTOR_VALUE_FIELDS))
    if unknown:
        raise ValueError(
            f"Unknown Descriptor v1 value fields: {unknown}"
        )

    record: dict[str, Any] = {
        field: None for field in DESCRIPTOR_RECORD_FIELDS
    }
    record.update(
        {
            "sample_uid": result.sample_uid,
            "structure_id": result.structure_id,
            "model_name": result.model_name,
            "model_short": result.model_short,
            "run_uid": result.run_uid,
            "source_sample_id": result.source_sample_id,
            "cif_path": result.cif_path,
            "descriptor_schema_version": result.schema_version,
            "descriptor_v1_source": result.source,
            "descriptor_v1_status": result.status.value,
            "descriptor_v1_error_code": result.error_code,
            "descriptor_v1_error_message": result.error_message,
        }
    )
    record.update(result.values)
    return record
