from __future__ import annotations

from collections.abc import Collection
from typing import Any

from .composition import compute_composition_descriptors
from .element_properties import compute_element_property_descriptors
from .local_geometry import compute_local_geometry_descriptors
from .schema import DescriptorInput, DescriptorResult, DescriptorStatus
from .structure import (
    compute_symmetry_descriptors,
    compute_unit_cell_descriptors,
)


def extract_descriptor_v1(
    descriptor_input: DescriptorInput,
    *,
    magnetic_screening_elements: Collection[str],
    symprec: float = 0.01,
    angle_tolerance: float = 5.0,
    local_geometry_cutoff: float = 10.0,
    local_geometry_tolerance: float = 0.1,
    local_geometry_get_all_sites: bool = False,
) -> DescriptorResult:
    """Compute all Descriptor v1 values for one structure."""

    values: dict[str, Any] = {}
    partial_reasons: list[str] = []

    try:
        values.update(
            compute_unit_cell_descriptors(descriptor_input.structure)
        )
    except Exception as exc:
        return DescriptorResult(
            sample_uid=descriptor_input.sample_uid,
            structure_id=descriptor_input.structure_id,
            status=DescriptorStatus.ERROR,
            model_name=descriptor_input.model_name,
            model_short=descriptor_input.model_short,
            run_uid=descriptor_input.run_uid,
            source_sample_id=descriptor_input.source_sample_id,
            cif_path=descriptor_input.cif_path,
            error_code="core_structure_descriptor_error",
            error_message=str(exc),
            values=values,
        )

    symmetry = compute_symmetry_descriptors(
        descriptor_input.structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )
    values.update(symmetry)

    if symmetry["symmetry_status"] != "ok":
        partial_reasons.append("symmetry_analysis_error")

    try:
        values.update(
            compute_composition_descriptors(
                descriptor_input.structure.composition,
                magnetic_screening_elements=magnetic_screening_elements,
            )
        )
    except Exception as exc:
        return DescriptorResult(
            sample_uid=descriptor_input.sample_uid,
            structure_id=descriptor_input.structure_id,
            status=DescriptorStatus.ERROR,
            model_name=descriptor_input.model_name,
            model_short=descriptor_input.model_short,
            run_uid=descriptor_input.run_uid,
            source_sample_id=descriptor_input.source_sample_id,
            cif_path=descriptor_input.cif_path,
            error_code="core_composition_descriptor_error",
            error_message=str(exc),
            values=values,
        )

    try:
        element_properties = compute_element_property_descriptors(
            descriptor_input.structure.composition
        )
        values.update(element_properties)

        incomplete_properties = sorted(
            field.removesuffix("_coverage")
            for field, value in element_properties.items()
            if field.endswith("_coverage")
            and value is not None
            and float(value) < 1.0 - 1e-12
        )
        if incomplete_properties:
            partial_reasons.append(
                "element_property_incomplete_coverage:"
                + ",".join(incomplete_properties)
            )
    except Exception as exc:
        partial_reasons.append(
            f"element_property_descriptor_error:{exc}"
        )

    local_geometry = compute_local_geometry_descriptors(
        descriptor_input.structure,
        cutoff=local_geometry_cutoff,
        tolerance=local_geometry_tolerance,
        get_all_sites=local_geometry_get_all_sites,
    )
    values.update(local_geometry)

    if local_geometry["local_geometry_status"] != "ok":
        partial_reasons.append("local_geometry_error")

    if partial_reasons:
        return DescriptorResult(
            sample_uid=descriptor_input.sample_uid,
            structure_id=descriptor_input.structure_id,
            status=DescriptorStatus.PARTIAL,
            model_name=descriptor_input.model_name,
            model_short=descriptor_input.model_short,
            run_uid=descriptor_input.run_uid,
            source_sample_id=descriptor_input.source_sample_id,
            cif_path=descriptor_input.cif_path,
            error_code="partial_descriptor_result",
            error_message="; ".join(partial_reasons),
            values=values,
        )

    return DescriptorResult(
        sample_uid=descriptor_input.sample_uid,
        structure_id=descriptor_input.structure_id,
        status=DescriptorStatus.OK,
        model_name=descriptor_input.model_name,
        model_short=descriptor_input.model_short,
        run_uid=descriptor_input.run_uid,
        source_sample_id=descriptor_input.source_sample_id,
        cif_path=descriptor_input.cif_path,
        values=values,
    )
