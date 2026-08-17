from __future__ import annotations

from collections.abc import Collection
from typing import Any

from ..magnetism.config import MagneticElementGroups
from .magnetic_composition import compute_magnetic_composition_descriptors
from .magnetic_geometry import (
    MAGNETIC_GEOMETRY_FIELDS,
    compute_magnetic_geometry_descriptors,
)
from .magnetic_symmetry import compute_magnetic_symmetry_descriptors
from .schema_v2 import (
    MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS,
    DescriptorV2Status,
    MagneticDescriptorInput,
    MagneticDescriptorResult,
)


def _empty_scientific_values() -> dict[str, Any]:
    return {
        field: None for field in MAGNETIC_DESCRIPTOR_V2_SCIENTIFIC_FIELDS
    }


def _result(
    descriptor_input: MagneticDescriptorInput,
    *,
    status: DescriptorV2Status,
    values: dict[str, Any],
    error_code: str = "",
    error_message: str = "",
) -> MagneticDescriptorResult:
    return MagneticDescriptorResult(
        sample_uid=descriptor_input.sample_uid,
        structure_id=descriptor_input.structure_id,
        status=status,
        analysis_cohort=descriptor_input.analysis_cohort,
        analysis_family=descriptor_input.analysis_family,
        analysis_state=descriptor_input.analysis_state,
        model_name=descriptor_input.model_name,
        model_short=descriptor_input.model_short,
        formula_reduced=descriptor_input.formula_reduced,
        formula_full_canonical=descriptor_input.formula_full_canonical,
        cif_path=descriptor_input.cif_path,
        error_code=error_code,
        error_message=error_message,
        values=values,
    )


def extract_magnetic_descriptor_v2(
    descriptor_input: MagneticDescriptorInput,
    *,
    magnetic_elements: MagneticElementGroups,
    configured_magnetic_elements: Collection[str] | None = None,
    symprec: float = 0.01,
    angle_tolerance: float = 5.0,
    local_geometry_cutoff: float = 10.0,
    local_geometry_tolerance: float = 0.1,
    local_geometry_get_all_sites: bool = False,
) -> MagneticDescriptorResult:
    values = _empty_scientific_values()
    partial_reasons: list[str] = []
    configured = (
        frozenset(configured_magnetic_elements)
        if configured_magnetic_elements is not None
        else magnetic_elements.all_elements
    )

    try:
        values.update(
            compute_magnetic_composition_descriptors(
                descriptor_input.structure.composition,
                magnetic_elements,
            )
        )
    except Exception as exc:
        values["magnetic_geometry_status"] = "not_computed"
        values["magnetic_symmetry_status"] = "not_computed"
        return _result(
            descriptor_input,
            status=DescriptorV2Status.ERROR,
            values=values,
            error_code="magnetic_composition_descriptor_error",
            error_message=str(exc),
        )

    try:
        geometry = compute_magnetic_geometry_descriptors(
            descriptor_input.structure,
            configured_magnetic_elements=configured,
            cutoff=local_geometry_cutoff,
            tolerance=local_geometry_tolerance,
            get_all_sites=local_geometry_get_all_sites,
        )
        values.update(geometry)
        if geometry["magnetic_geometry_status"] == "error":
            partial_reasons.append("magnetic_geometry_error")
    except Exception as exc:
        for field in MAGNETIC_GEOMETRY_FIELDS:
            values[field] = None
        values["magnetic_geometry_status"] = "error"
        partial_reasons.append(f"magnetic_geometry_error:{exc}")

    try:
        values.update(
            compute_magnetic_symmetry_descriptors(
                descriptor_input.structure,
                configured_magnetic_elements=configured,
                symprec=symprec,
                angle_tolerance=angle_tolerance,
            )
        )
    except Exception as exc:
        values.update(
            {
                "n_symmetry_unique_sites": None,
                "symmetry_unique_site_fraction": None,
                "n_symmetry_unique_magnetic_sites": None,
                "symmetry_unique_magnetic_site_fraction": None,
                "site_multiplicity_entropy": None,
                "magnetic_symmetry_status": "error",
            }
        )
        partial_reasons.append(f"magnetic_symmetry_error:{exc}")

    if partial_reasons:
        return _result(
            descriptor_input,
            status=DescriptorV2Status.PARTIAL,
            values=values,
            error_code="partial_descriptor_v2_result",
            error_message="; ".join(partial_reasons),
        )

    return _result(
        descriptor_input,
        status=DescriptorV2Status.OK,
        values=values,
    )
