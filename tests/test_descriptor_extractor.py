from __future__ import annotations

import pytest
from pymatgen.core import Lattice, Structure

from mvpipeline.descriptors.extractor import extract_descriptor_v1
from mvpipeline.descriptors.records import (
    DESCRIPTOR_RECORD_FIELDS,
    descriptor_result_to_record,
)
from mvpipeline.descriptors.schema import (
    DescriptorInput,
    DescriptorStatus,
)


def test_complete_structure_produces_ok_descriptor_result():
    structure = Structure(
        Lattice.cubic(3.0),
        ["Fe"],
        [[0.0, 0.0, 0.0]],
    )
    descriptor_input = DescriptorInput(
        sample_uid="sample__ok",
        structure_id="sample__ok",
        structure=structure,
    )

    result = extract_descriptor_v1(
        descriptor_input,
        magnetic_screening_elements={"Fe"},
    )
    record = descriptor_result_to_record(result)

    assert result.status is DescriptorStatus.OK
    assert result.error_code == ""
    assert result.error_message == ""
    assert len(result.values) == 72
    assert len(record) == 84
    assert list(record) == DESCRIPTOR_RECORD_FIELDS
    assert record["descriptor_v1_status"] == "ok"
    assert record["symmetry_status"] == "ok"
    assert record["local_geometry_status"] == "ok"


def test_incomplete_element_property_coverage_produces_partial_result():
    structure = Structure(
        Lattice.cubic(4.0),
        ["Fe", "He"],
        [
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5],
        ],
    )
    descriptor_input = DescriptorInput(
        sample_uid="sample__partial",
        structure_id="sample__partial",
        structure=structure,
    )

    result = extract_descriptor_v1(
        descriptor_input,
        magnetic_screening_elements={"Fe"},
    )
    record = descriptor_result_to_record(result)

    assert result.status is DescriptorStatus.PARTIAL
    assert result.error_code == "partial_descriptor_result"
    assert "element_property_incomplete_coverage:" in result.error_message
    assert "atomic_radius" in result.error_message
    assert "electronegativity" in result.error_message
    assert len(result.values) == 72

    assert record["descriptor_v1_status"] == "partial"
    assert record["atomic_radius_coverage"] == pytest.approx(0.5)
    assert record["atomic_radius_mean"] is None
    assert record["electronegativity_coverage"] == pytest.approx(0.5)
    assert record["electronegativity_mean"] is None


def test_core_structure_failure_produces_error_result():
    descriptor_input = DescriptorInput(
        sample_uid="sample__error",
        structure_id="sample__error",
        structure=object(),
    )

    result = extract_descriptor_v1(
        descriptor_input,
        magnetic_screening_elements={"Fe"},
    )
    record = descriptor_result_to_record(result)

    assert result.status is DescriptorStatus.ERROR
    assert result.error_code == "core_structure_descriptor_error"
    assert result.error_message
    assert result.values == {}

    assert len(record) == 84
    assert record["descriptor_v1_status"] == "error"
    assert record["density"] is None
    assert record["symmetry_status"] is None
    assert record["local_geometry_status"] is None
