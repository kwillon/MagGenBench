from __future__ import annotations

import csv

from pymatgen.core import Lattice, Structure

from mvpipeline.descriptors.batch import run_descriptor_batch
from mvpipeline.descriptors.records import DESCRIPTOR_RECORD_FIELDS


def simple_structure(symbol: str) -> Structure:
    return Structure(
        Lattice.cubic(3.0),
        [symbol],
        [[0.0, 0.0, 0.0]],
    )


def test_run_descriptor_batch_writes_row_preserving_csv(tmp_path):
    input_path = tmp_path / "manifest.csv"
    output_path = tmp_path / "descriptors.csv"

    input_rows = [
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

    with input_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_uid",
                "structure_id",
                "cif_path",
            ],
        )
        writer.writeheader()
        writer.writerows(input_rows)

    def loader(path: str):
        if path == "broken.cif":
            raise ValueError("synthetic CIF parse failure")
        if path == "a.cif":
            return simple_structure("Fe")
        return simple_structure("Co")

    report = run_descriptor_batch(
        input_path=input_path,
        output_path=output_path,
        descriptor_config_path="config/descriptors.yaml",
        project_root=".",
        structure_loader=loader,
    )

    assert report.input_count == 3
    assert report.output_count == 3
    assert report.output_path == output_path
    assert report.fieldnames == DESCRIPTOR_RECORD_FIELDS

    with output_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        output_rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    assert fieldnames == DESCRIPTOR_RECORD_FIELDS
    assert len(fieldnames) == 84
    assert len(output_rows) == 3

    assert [row["sample_uid"] for row in output_rows] == [
        "sample__a",
        "sample__b",
        "sample__c",
    ]

    assert output_rows[0]["descriptor_v1_status"] == "ok"
    assert output_rows[1]["descriptor_v1_status"] == "error"
    assert (
        output_rows[1]["descriptor_v1_error_code"]
        == "cif_parse_error"
    )
    assert "synthetic CIF parse failure" in output_rows[1][
        "descriptor_v1_error_message"
    ]
    assert output_rows[2]["descriptor_v1_status"] == "ok"
