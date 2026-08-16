from __future__ import annotations

import pytest

from mvpipeline.descriptors.records import (
    DESCRIPTOR_RECORD_FIELDS,
    DESCRIPTOR_VALUE_FIELDS,
    descriptor_result_to_record,
)
from mvpipeline.descriptors.schema import (
    DESCRIPTOR_SCHEMA_VERSION,
    DESCRIPTOR_SOURCE,
    DescriptorResult,
    DescriptorStatus,
)


def test_descriptor_v1_record_contract_is_frozen():
    assert len(DESCRIPTOR_RECORD_FIELDS) == 84
    assert len(DESCRIPTOR_VALUE_FIELDS) == 72
    assert len(set(DESCRIPTOR_RECORD_FIELDS)) == 84

    assert DESCRIPTOR_RECORD_FIELDS[:7] == [
        "sample_uid",
        "structure_id",
        "model_name",
        "model_short",
        "run_uid",
        "source_sample_id",
        "cif_path",
    ]

    assert DESCRIPTOR_RECORD_FIELDS[-5:] == [
        "descriptor_schema_version",
        "descriptor_v1_source",
        "descriptor_v1_status",
        "descriptor_v1_error_code",
        "descriptor_v1_error_message",
    ]


def test_descriptor_result_flattens_to_complete_record():
    result = DescriptorResult(
        sample_uid="sample__0001",
        structure_id="sample__0001",
        status=DescriptorStatus.OK,
        model_name="Example",
        model_short="example",
        run_uid="run-1",
        source_sample_id="0001",
        cif_path="samples/example__0001.cif",
        values={
            "n_atoms": 4,
            "density": 7.5,
            "symmetry_status": "ok",
            "local_geometry_status": "ok",
        },
    )

    record = descriptor_result_to_record(result)

    assert list(record) == DESCRIPTOR_RECORD_FIELDS
    assert len(record) == 84
    assert record["sample_uid"] == "sample__0001"
    assert record["structure_id"] == "sample__0001"
    assert record["n_atoms"] == 4
    assert record["density"] == 7.5
    assert record["descriptor_schema_version"] == DESCRIPTOR_SCHEMA_VERSION
    assert record["descriptor_v1_source"] == DESCRIPTOR_SOURCE
    assert record["descriptor_v1_status"] == "ok"
    assert record["descriptor_v1_error_code"] == ""
    assert record["descriptor_v1_error_message"] == ""


def test_descriptor_result_keeps_missing_values_explicit():
    result = DescriptorResult(
        sample_uid="sample__0002",
        structure_id="sample__0002",
        status=DescriptorStatus.PARTIAL,
        values={"symmetry_status": "error"},
    )

    record = descriptor_result_to_record(result)

    assert record["symmetry_status"] == "error"
    assert record["density"] is None
    assert record["nearest_neighbor_mean"] is None
    assert record["descriptor_v1_status"] == "partial"


def test_descriptor_result_rejects_unknown_value_field():
    result = DescriptorResult(
        sample_uid="sample__0003",
        structure_id="sample__0003",
        status=DescriptorStatus.OK,
        values={"not_a_descriptor": 1.0},
    )

    with pytest.raises(ValueError, match="Unknown Descriptor v1 value fields"):
        descriptor_result_to_record(result)
