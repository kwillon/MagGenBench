from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from mvpipeline.analysis.magnetic_v2 import (
    DESCRIPTOR_V2_MAGNETIC_PATH,
    EXPECTED_ANALYSIS_V2_COHORT_COUNTS,
    EXPECTED_ANALYSIS_V2_COLUMNS,
    EXPECTED_DESCRIPTOR_V2_COLUMNS,
    EXPECTED_STANDARDIZED_COLUMNS,
    OVERLAPPING_IDENTITY_FIELDS,
    STANDARDIZED_ENRICHMENT_PATH,
    build_analysis_v2_magnetic,
    read_csv_table,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

STD_FIELDS = [
    "analysis_cohort",
    "analysis_family",
    "analysis_state",
    "structure_id",
    "sample_uid",
    "model_name",
    "model_short",
    "formula_reduced",
    "formula_full_canonical",
    "cif_path",
    "energy_status",
]

DESC_FIELDS = [
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
    "transition_3d_fraction",
    "descriptor_v2_status",
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def std_row(structure_id: str, *, cohort: str = "mattergen_baseline") -> dict[str, str]:
    return {
        "analysis_cohort": cohort,
        "analysis_family": "MatterGen",
        "analysis_state": "baseline",
        "structure_id": structure_id,
        "sample_uid": structure_id,
        "model_name": "MatterGen",
        "model_short": "mg",
        "formula_reduced": "Fe",
        "formula_full_canonical": "Fe1",
        "cif_path": f"samples/{structure_id}.cif",
        "energy_status": "ok",
    }


def desc_row(structure_id: str, *, cohort: str = "mattergen_baseline") -> dict[str, str]:
    row = std_row(structure_id, cohort=cohort)
    return {
        field: row[field]
        for field in OVERLAPPING_IDENTITY_FIELDS
    } | {
        "transition_3d_fraction": "1.0",
        "descriptor_v2_status": "ok",
    }


def build_small(
    tmp_path: Path,
    std_rows: list[dict[str, str]],
    desc_rows: list[dict[str, str]],
):
    std_path = tmp_path / "standardized.csv"
    desc_path = tmp_path / "descriptor_v2.csv"
    output_path = tmp_path / "analysis_v2.csv"
    write_csv(std_path, STD_FIELDS, std_rows)
    write_csv(desc_path, DESC_FIELDS, desc_rows)
    report = build_analysis_v2_magnetic(
        standardized_enrichment_path=std_path,
        descriptor_v2_path=desc_path,
        output_path=output_path,
        expected_rows=None,
        expected_standardized_columns=len(STD_FIELDS),
        expected_descriptor_v2_columns=len(DESC_FIELDS),
        expected_output_columns=len(STD_FIELDS) + len(DESC_FIELDS) - 10,
        expected_cohort_counts=None,
    )
    return report, output_path


def test_analysis_v2_successful_join_preserves_order_and_removes_duplicates(tmp_path):
    report, output_path = build_small(
        tmp_path,
        [std_row("s2"), std_row("s1")],
        [desc_row("s1"), desc_row("s2")],
    )

    fieldnames, rows = read_rows(output_path)

    assert report.output_rows == 2
    assert report.output_columns == 13
    assert [row["structure_id"] for row in rows] == ["s2", "s1"]
    assert fieldnames == [
        *STD_FIELDS,
        "transition_3d_fraction",
        "descriptor_v2_status",
    ]
    assert "analysis_cohort_x" not in fieldnames
    assert "analysis_cohort_y" not in fieldnames
    assert fieldnames.count("structure_id") == 1


def test_analysis_v2_output_is_deterministic(tmp_path):
    _, output_path = build_small(
        tmp_path,
        [std_row("s1"), std_row("s2")],
        [desc_row("s2"), desc_row("s1")],
    )
    first = output_path.read_bytes()

    _, output_path = build_small(
        tmp_path,
        [std_row("s1"), std_row("s2")],
        [desc_row("s2"), desc_row("s1")],
    )
    assert output_path.read_bytes() == first


def test_analysis_v2_duplicate_structure_id_failure(tmp_path):
    with pytest.raises(RuntimeError, match="duplicate structure_id"):
        build_small(
            tmp_path,
            [std_row("s1"), std_row("s1")],
            [desc_row("s1"), desc_row("s2")],
        )


def test_analysis_v2_duplicate_sample_uid_failure(tmp_path):
    duplicate = [std_row("s1"), std_row("s2")]
    duplicate[1]["sample_uid"] = "s1"

    with pytest.raises(RuntimeError, match="duplicate sample_uid"):
        build_small(tmp_path, duplicate, [desc_row("s1"), desc_row("s2")])


def test_analysis_v2_sample_uid_must_equal_structure_id(tmp_path):
    bad = [std_row("s1")]
    bad[0]["sample_uid"] = "different"

    with pytest.raises(RuntimeError, match="sample_uid != structure_id"):
        build_small(tmp_path, bad, [desc_row("s1")])


def test_analysis_v2_missing_id_in_descriptor_failure(tmp_path):
    with pytest.raises(RuntimeError, match="missing_in_descriptor"):
        build_small(
            tmp_path,
            [std_row("s1"), std_row("s2")],
            [desc_row("s1")],
        )


def test_analysis_v2_extra_id_in_descriptor_failure(tmp_path):
    with pytest.raises(RuntimeError, match="extra_in_descriptor"):
        build_small(
            tmp_path,
            [std_row("s1")],
            [desc_row("s1"), desc_row("s2")],
        )


def test_analysis_v2_overlapping_identity_mismatch_failure(tmp_path):
    mismatched = desc_row("s1")
    mismatched["formula_reduced"] = "Co"

    with pytest.raises(RuntimeError, match="overlapping identity fields differ"):
        build_small(tmp_path, [std_row("s1")], [mismatched])


def test_analysis_v2_production_style_cohort_count_mismatch_fails(tmp_path):
    std_path = tmp_path / "standardized.csv"
    desc_path = tmp_path / "descriptor_v2.csv"
    output_path = tmp_path / "analysis_v2.csv"
    write_csv(std_path, STD_FIELDS, [std_row("s1")])
    write_csv(desc_path, DESC_FIELDS, [desc_row("s1")])

    with pytest.raises(RuntimeError, match="analysis_cohort counts differ"):
        build_analysis_v2_magnetic(
            standardized_enrichment_path=std_path,
            descriptor_v2_path=desc_path,
            output_path=output_path,
            expected_rows=None,
            expected_standardized_columns=len(STD_FIELDS),
            expected_descriptor_v2_columns=len(DESC_FIELDS),
            expected_output_columns=len(STD_FIELDS) + len(DESC_FIELDS) - 10,
            expected_cohort_counts={
                "mattergen_baseline": 2,
            },
        )


def test_analysis_v2_real_canonical_headers_have_expected_shape_and_overlap():
    std_fields, _ = read_csv_table(REPO_ROOT / STANDARDIZED_ENRICHMENT_PATH)
    desc_fields, _ = read_csv_table(REPO_ROOT / DESCRIPTOR_V2_MAGNETIC_PATH)

    overlap = tuple(field for field in std_fields if field in desc_fields)

    assert len(std_fields) == EXPECTED_STANDARDIZED_COLUMNS
    assert len(desc_fields) == EXPECTED_DESCRIPTOR_V2_COLUMNS
    assert overlap == OVERLAPPING_IDENTITY_FIELDS
    assert len(std_fields) + len(desc_fields) - len(overlap) == (
        EXPECTED_ANALYSIS_V2_COLUMNS
    )


def test_analysis_v2_real_canonical_inputs_have_expected_cohort_counts():
    _, std_rows = read_csv_table(REPO_ROOT / STANDARDIZED_ENRICHMENT_PATH)
    _, desc_rows = read_csv_table(REPO_ROOT / DESCRIPTOR_V2_MAGNETIC_PATH)

    def counts(rows):
        return Counter(row["analysis_cohort"] for row in rows)

    assert counts(std_rows) == EXPECTED_ANALYSIS_V2_COHORT_COUNTS
    assert counts(desc_rows) == EXPECTED_ANALYSIS_V2_COHORT_COUNTS
