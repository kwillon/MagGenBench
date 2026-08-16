from __future__ import annotations

import pytest
from pymatgen.core import Lattice, Structure

from mvpipeline.descriptors.batch import extract_descriptor_rows
from mvpipeline.descriptors.config import DescriptorRuntimeConfig
from mvpipeline.descriptors.records import DESCRIPTOR_RECORD_FIELDS


def runtime_config() -> DescriptorRuntimeConfig:
    return DescriptorRuntimeConfig(
        schema_version="v1",
        reference_pymatgen_version="2025.6.14",
        symprec=0.01,
        angle_tolerance=5.0,
        local_geometry_method="MinimumDistanceNN",
        local_geometry_cutoff=10.0,
        local_geometry_tolerance=0.1,
        local_geometry_get_all_sites=False,
        local_geometry_use_weights=False,
        magnetic_screening_elements=frozenset({"Fe", "Co"}),
    )


def simple_structure(symbol: str) -> Structure:
    return Structure(
        Lattice.cubic(3.0),
        [symbol],
        [[0.0, 0.0, 0.0]],
    )


def test_batch_preserves_rows_order_and_parse_errors():
    rows = [
        {
            "sample_uid": "sample__a",
            "structure_id": "sample__a",
            "cif_path": "a.cif",
        },
        {
            "sample_uid": "sample__b",
            "structure_id": "sample__b",
            "cif_path": "broken.cif",
        },
        {
            "sample_uid": "sample__c",
            "structure_id": "sample__c",
            "cif_path": "c.cif",
        },
    ]

    def loader(path: str):
        if path == "broken.cif":
            raise ValueError("synthetic CIF parse failure")
        if path == "a.cif":
            return simple_structure("Fe")
        return simple_structure("Co")

    output = extract_descriptor_rows(
        rows,
        config=runtime_config(),
        structure_loader=loader,
    )

    assert len(output) == len(rows) == 3
    assert [row["sample_uid"] for row in output] == [
        "sample__a",
        "sample__b",
        "sample__c",
    ]

    assert output[0]["descriptor_v1_status"] == "ok"

    assert output[1]["descriptor_v1_status"] == "error"
    assert output[1]["descriptor_v1_error_code"] == "cif_parse_error"
    assert "synthetic CIF parse failure" in output[1][
        "descriptor_v1_error_message"
    ]

    assert output[2]["descriptor_v1_status"] == "ok"

    for row in output:
        assert list(row) == DESCRIPTOR_RECORD_FIELDS
        assert len(row) == 84


def test_batch_rejects_duplicate_sample_uid():
    rows = [
        {
            "sample_uid": "duplicate",
            "structure_id": "duplicate",
            "cif_path": "a.cif",
        },
        {
            "sample_uid": "duplicate",
            "structure_id": "other",
            "cif_path": "b.cif",
        },
    ]

    with pytest.raises(ValueError, match="Duplicate sample_uid"):
        extract_descriptor_rows(
            rows,
            config=runtime_config(),
        )


def test_batch_requires_sample_uid_equal_structure_id():
    rows = [
        {
            "sample_uid": "sample__a",
            "structure_id": "different__id",
            "cif_path": "a.cif",
        },
    ]

    with pytest.raises(
        ValueError,
        match="sample_uid == structure_id",
    ):
        extract_descriptor_rows(
            rows,
            config=runtime_config(),
        )
