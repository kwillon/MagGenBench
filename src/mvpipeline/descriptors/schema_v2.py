from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


DESCRIPTOR_V2_SCHEMA_VERSION = "v2-magnetic"
DESCRIPTOR_V2_SOURCE = "cif_recomputed"

MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS = (
    "transition_3d_fraction",
    "selected_4d_5d_fraction",
    "configured_lanthanide_fraction",
    "n_transition_3d_species",
    "n_selected_4d_5d_species",
    "n_configured_lanthanide_species",
    "contains_3d_and_configured_lanthanide",
    "magnetic_site_nearest_neighbor_distance_min",
    "magnetic_site_nearest_neighbor_distance_mean",
    "magnetic_site_nearest_neighbor_distance_std",
    "magnetic_site_nearest_magnetic_neighbor_distance_min",
    "magnetic_site_nearest_magnetic_neighbor_distance_mean",
    "magnetic_site_nearest_magnetic_neighbor_distance_std",
    "magnetic_site_coordination_mean",
    "magnetic_site_coordination_std",
    "magnetic_site_magnetic_coordination_mean",
    "magnetic_site_magnetic_coordination_std",
    "magnetic_site_magnetic_neighbor_fraction_mean",
    "magnetic_site_magnetic_neighbor_fraction_std",
    "n_symmetry_unique_sites",
    "symmetry_unique_site_fraction",
    "n_symmetry_unique_magnetic_sites",
    "symmetry_unique_magnetic_site_fraction",
    "site_multiplicity_entropy",
)

MAGNETIC_DESCRIPTOR_V2_IDENTITY_FIELDS = (
    "sample_uid",
    "structure_id",
    "analysis_cohort",
    "analysis_family",
    "analysis_state",
    "model_name",
    "model_short",
    "formula_reduced",
    "formula_full_canonical",
    "cif_path",
)

MAGNETIC_DESCRIPTOR_V2_STATUS_FIELDS = (
    "descriptor_v2_schema_version",
    "descriptor_v2_source",
    "descriptor_v2_status",
    "descriptor_v2_error_code",
    "descriptor_v2_error_message",
    "magnetic_geometry_status",
    "magnetic_symmetry_status",
)

MAGNETIC_DESCRIPTOR_V2_RECORD_FIELDS = (
    *MAGNETIC_DESCRIPTOR_V2_IDENTITY_FIELDS,
    *MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS,
    *MAGNETIC_DESCRIPTOR_V2_STATUS_FIELDS,
)


class DescriptorV2Status(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass(frozen=True)
class MagneticDescriptorInput:
    sample_uid: str
    structure_id: str
    structure: Any
    analysis_cohort: str = ""
    analysis_family: str = ""
    analysis_state: str = ""
    model_name: str = ""
    model_short: str = ""
    formula_reduced: str = ""
    formula_full_canonical: str = ""
    cif_path: str = ""


@dataclass(frozen=True)
class MagneticDescriptorResult:
    sample_uid: str
    structure_id: str
    status: DescriptorV2Status
    analysis_cohort: str = ""
    analysis_family: str = ""
    analysis_state: str = ""
    model_name: str = ""
    model_short: str = ""
    formula_reduced: str = ""
    formula_full_canonical: str = ""
    cif_path: str = ""
    error_code: str = ""
    error_message: str = ""
    source: str = DESCRIPTOR_V2_SOURCE
    schema_version: str = DESCRIPTOR_V2_SCHEMA_VERSION
    values: Mapping[str, Any] = field(default_factory=dict)


def magnetic_descriptor_v2_result_to_record(
    result: MagneticDescriptorResult,
) -> dict[str, Any]:
    allowed = set(MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS) | {
        "magnetic_geometry_status",
        "magnetic_symmetry_status",
    }
    unknown = sorted(set(result.values) - allowed)
    if unknown:
        raise ValueError(f"Unknown Descriptor v2 value fields: {unknown}")

    record: dict[str, Any] = {
        field: None for field in MAGNETIC_DESCRIPTOR_V2_RECORD_FIELDS
    }
    record.update(
        {
            "sample_uid": result.sample_uid,
            "structure_id": result.structure_id,
            "analysis_cohort": result.analysis_cohort,
            "analysis_family": result.analysis_family,
            "analysis_state": result.analysis_state,
            "model_name": result.model_name,
            "model_short": result.model_short,
            "formula_reduced": result.formula_reduced,
            "formula_full_canonical": result.formula_full_canonical,
            "cif_path": result.cif_path,
            "descriptor_v2_schema_version": result.schema_version,
            "descriptor_v2_source": result.source,
            "descriptor_v2_status": result.status.value,
            "descriptor_v2_error_code": result.error_code,
            "descriptor_v2_error_message": result.error_message,
        }
    )
    record.update(result.values)
    return record
