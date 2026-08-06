import csv
from pathlib import Path

import pytest

from mvpipeline.pipeline.enrichment_results_join import (
    join_enrichment_result_rows,
    run_enrichment_results_join,
)


ANNOTATION_FIELDS = [
    "sample_uid",
    "structure_id",
    "model_name",
    "status",
]

ENERGY_FIELDS = [
    "structure_id",
    "status",
    "error_code",
    "model_name",
    "formation_energy_proxy_eV",
]

MAGNETISM_FIELDS = [
    "structure_id",
    "status",
    "error_code",
    "model_name",
    "predicted_moment_value",
    "moment_unit",
]


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        return list(csv.DictReader(handle))


def annotation_rows():
    return [
        {
            "sample_uid": "s1",
            "structure_id": "s1",
            "model_name": "generator-a",
            "status": "accepted",
        },
        {
            "sample_uid": "s2",
            "structure_id": "s2",
            "model_name": "generator-b",
            "status": "accepted",
        },
        {
            "sample_uid": "s3",
            "structure_id": "s3",
            "model_name": "generator-c",
            "status": "rejected",
        },
    ]


def energy_rows():
    return [
        {
            "structure_id": "s1",
            "status": "ok",
            "error_code": "",
            "model_name": "energy-model",
            "formation_energy_proxy_eV": "-1.2",
        },
        {
            "structure_id": "s3",
            "status": "error",
            "error_code": "prediction_failed",
            "model_name": "energy-model",
            "formation_energy_proxy_eV": "",
        },
    ]


def magnetism_rows():
    return [
        {
            "structure_id": "s1",
            "status": "ok",
            "error_code": "",
            "model_name": "dxmag",
            "predicted_moment_value": "0.3",
            "moment_unit": "uB/f.u.",
        },
        {
            "structure_id": "s2",
            "status": "error",
            "error_code": "feature_error",
            "model_name": "dxmag",
            "predicted_moment_value": "",
            "moment_unit": "uB/f.u.",
        },
    ]


def test_join_preserves_base_order_and_namespaces_stage_fields():
    rows, fields = join_enrichment_result_rows(
        annotation_rows(),
        annotation_fieldnames=ANNOTATION_FIELDS,
        energy_rows=energy_rows(),
        energy_fieldnames=ENERGY_FIELDS,
        magnetism_rows=magnetism_rows(),
        magnetism_fieldnames=MAGNETISM_FIELDS,
    )

    assert [
        row["sample_uid"]
        for row in rows
    ] == ["s1", "s2", "s3"]

    assert rows[0]["status"] == "accepted"
    assert rows[0]["model_name"] == "generator-a"

    assert rows[0]["energy_status"] == "ok"
    assert (
        rows[0]["energy_model_name"]
        == "energy-model"
    )
    assert (
        rows[0]["energy_formation_energy_proxy_eV"]
        == "-1.2"
    )

    assert rows[0]["magnetism_status"] == "ok"
    assert (
        rows[0]["magnetism_model_name"]
        == "dxmag"
    )
    assert (
        rows[0]["magnetism_predicted_moment_value"]
        == "0.3"
    )

    assert "energy_status" in fields
    assert "magnetism_status" in fields


def test_missing_results_are_explicit_and_do_not_drop_rows():
    rows, _ = join_enrichment_result_rows(
        annotation_rows(),
        annotation_fieldnames=ANNOTATION_FIELDS,
        energy_rows=energy_rows(),
        energy_fieldnames=ENERGY_FIELDS,
        magnetism_rows=magnetism_rows(),
        magnetism_fieldnames=MAGNETISM_FIELDS,
    )

    by_id = {
        row["sample_uid"]: row
        for row in rows
    }

    assert (
        by_id["s2"]["energy_join_status"]
        == "missing"
    )
    assert by_id["s2"]["energy_status"] == ""

    assert (
        by_id["s3"]["magnetism_join_status"]
        == "missing"
    )
    assert by_id["s3"]["magnetism_status"] == ""

    assert (
        by_id["s3"]["energy_join_status"]
        == "matched"
    )
    assert by_id["s3"]["energy_status"] == "error"


@pytest.mark.parametrize(
    ("table_name", "duplicate_rows", "match"),
    [
        (
            "annotations",
            [
                annotation_rows()[0],
                annotation_rows()[0],
            ],
            "Duplicate sample_uid",
        ),
        (
            "energy",
            [
                energy_rows()[0],
                energy_rows()[0],
            ],
            "Duplicate structure_id",
        ),
        (
            "magnetism",
            [
                magnetism_rows()[0],
                magnetism_rows()[0],
            ],
            "Duplicate structure_id",
        ),
    ],
)
def test_duplicate_keys_are_rejected(
    table_name,
    duplicate_rows,
    match,
):
    annotations = annotation_rows()
    energy = energy_rows()
    magnetism = magnetism_rows()

    if table_name == "annotations":
        annotations = duplicate_rows
    elif table_name == "energy":
        energy = duplicate_rows
    else:
        magnetism = duplicate_rows

    with pytest.raises(ValueError, match=match):
        join_enrichment_result_rows(
            annotations,
            annotation_fieldnames=ANNOTATION_FIELDS,
            energy_rows=energy,
            energy_fieldnames=ENERGY_FIELDS,
            magnetism_rows=magnetism,
            magnetism_fieldnames=MAGNETISM_FIELDS,
        )


def test_phase5a1_table_requires_structure_id():
    fields = [
        field
        for field in ANNOTATION_FIELDS
        if field != "structure_id"
    ]

    annotations = [
        {
            field: row[field]
            for field in fields
        }
        for row in annotation_rows()
    ]

    with pytest.raises(
        ValueError,
        match="missing required columns.*structure_id",
    ):
        join_enrichment_result_rows(
            annotations,
            annotation_fieldnames=fields,
            energy_rows=energy_rows(),
            energy_fieldnames=ENERGY_FIELDS,
            magnetism_rows=magnetism_rows(),
            magnetism_fieldnames=MAGNETISM_FIELDS,
        )


def test_phase5a1_sample_uid_structure_id_mismatch_is_rejected():
    annotations = annotation_rows()
    annotations[0] = {
        **annotations[0],
        "structure_id": "different-id",
    }

    with pytest.raises(
        ValueError,
        match="Phase 5A-1 key mismatch",
    ):
        join_enrichment_result_rows(
            annotations,
            annotation_fieldnames=ANNOTATION_FIELDS,
            energy_rows=energy_rows(),
            energy_fieldnames=ENERGY_FIELDS,
            magnetism_rows=magnetism_rows(),
            magnetism_fieldnames=MAGNETISM_FIELDS,
        )


def test_unknown_stage_result_id_is_rejected_by_default():
    energy = [
        *energy_rows(),
        {
            "structure_id": "outside",
            "status": "ok",
            "error_code": "",
            "model_name": "energy-model",
            "formation_energy_proxy_eV": "-2.0",
        },
    ]

    with pytest.raises(
        ValueError,
        match="absent from Phase 5A-1",
    ):
        join_enrichment_result_rows(
            annotation_rows(),
            annotation_fieldnames=ANNOTATION_FIELDS,
            energy_rows=energy,
            energy_fieldnames=ENERGY_FIELDS,
            magnetism_rows=magnetism_rows(),
            magnetism_fieldnames=MAGNETISM_FIELDS,
        )


def test_unknown_stage_result_id_can_be_ignored_explicitly():
    energy = [
        *energy_rows(),
        {
            "structure_id": "outside",
            "status": "ok",
            "error_code": "",
            "model_name": "energy-model",
            "formation_energy_proxy_eV": "-2.0",
        },
    ]

    rows, _ = join_enrichment_result_rows(
        annotation_rows(),
        annotation_fieldnames=ANNOTATION_FIELDS,
        energy_rows=energy,
        energy_fieldnames=ENERGY_FIELDS,
        magnetism_rows=magnetism_rows(),
        magnetism_fieldnames=MAGNETISM_FIELDS,
        strict_result_ids=False,
    )

    assert [
        row["sample_uid"]
        for row in rows
    ] == ["s1", "s2", "s3"]


def test_file_runner_writes_atomic_join_and_report(tmp_path):
    annotations_path = (
        tmp_path / "annotations.csv"
    )
    energy_path = tmp_path / "energy.csv"
    magnetism_path = tmp_path / "magnetism.csv"
    output_path = tmp_path / "joined.csv"

    write_csv(
        annotations_path,
        ANNOTATION_FIELDS,
        annotation_rows(),
    )
    write_csv(
        energy_path,
        ENERGY_FIELDS,
        energy_rows(),
    )
    write_csv(
        magnetism_path,
        MAGNETISM_FIELDS,
        magnetism_rows(),
    )

    report = run_enrichment_results_join(
        annotations_path=annotations_path,
        energy_results_path=energy_path,
        magnetism_results_path=magnetism_path,
        output_path=output_path,
    )

    rows = read_csv(output_path)

    assert report.annotation_count == 3
    assert report.energy_result_count == 2
    assert report.magnetism_result_count == 2
    assert report.energy_matched_count == 2
    assert report.energy_missing_count == 1
    assert report.magnetism_matched_count == 2
    assert report.magnetism_missing_count == 1
    assert report.output_count == 3

    assert len(rows) == 3
    assert not output_path.with_name(
        output_path.name + ".tmp"
    ).exists()


def test_validation_error_does_not_replace_existing_output(
    tmp_path,
):
    annotations_path = (
        tmp_path / "annotations.csv"
    )
    energy_path = tmp_path / "energy.csv"
    magnetism_path = tmp_path / "magnetism.csv"
    output_path = tmp_path / "joined.csv"

    write_csv(
        annotations_path,
        ANNOTATION_FIELDS,
        annotation_rows(),
    )

    duplicate_energy = [
        energy_rows()[0],
        energy_rows()[0],
    ]

    write_csv(
        energy_path,
        ENERGY_FIELDS,
        duplicate_energy,
    )
    write_csv(
        magnetism_path,
        MAGNETISM_FIELDS,
        magnetism_rows(),
    )

    output_path.write_text(
        "old\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate structure_id",
    ):
        run_enrichment_results_join(
            annotations_path=annotations_path,
            energy_results_path=energy_path,
            magnetism_results_path=magnetism_path,
            output_path=output_path,
        )

    assert output_path.read_text(
        encoding="utf-8",
    ) == "old\n"


def test_header_only_annotation_table_writes_header_only_output(
    tmp_path,
):
    annotations_path = (
        tmp_path / "annotations.csv"
    )
    energy_path = tmp_path / "energy.csv"
    magnetism_path = tmp_path / "magnetism.csv"
    output_path = tmp_path / "joined.csv"

    write_csv(
        annotations_path,
        ANNOTATION_FIELDS,
        [],
    )
    write_csv(
        energy_path,
        ENERGY_FIELDS,
        [],
    )
    write_csv(
        magnetism_path,
        MAGNETISM_FIELDS,
        [],
    )

    report = run_enrichment_results_join(
        annotations_path=annotations_path,
        energy_results_path=energy_path,
        magnetism_results_path=magnetism_path,
        output_path=output_path,
    )

    rows = read_csv(output_path)

    assert report.output_count == 0
    assert rows == []

    header = output_path.read_text(
        encoding="utf-8",
    ).splitlines()[0]

    assert "energy_join_status" in header
    assert "magnetism_join_status" in header
    assert "energy_formation_energy_proxy_eV" in header
    assert "magnetism_predicted_moment_value" in header
