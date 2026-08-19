from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..io.stage_tables import write_stage_csv_atomic


STANDARDIZED_ENRICHMENT_PATH = Path(
    "tables/08_standardized_enrichment/standardized_enrichment.csv"
)
DESCRIPTOR_V2_MAGNETIC_PATH = Path(
    "tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv"
)
DEFAULT_ANALYSIS_V2_MAGNETIC_OUTPUT_PATH = Path(
    "reproduced/analysis_v2_magnetic/analysis_v2_magnetic.csv"
)

EXPECTED_STANDARDIZED_ROWS = 10684
EXPECTED_DESCRIPTOR_V2_ROWS = 10684
EXPECTED_ANALYSIS_V2_ROWS = 10684
EXPECTED_STANDARDIZED_COLUMNS = 87
EXPECTED_DESCRIPTOR_V2_COLUMNS = 41
EXPECTED_ANALYSIS_V2_COLUMNS = 118

OVERLAPPING_IDENTITY_FIELDS = (
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
)

EXPECTED_ANALYSIS_V2_COHORT_COUNTS = {
    "mattergen_baseline": 1657,
    "mattergen_finetuned": 1376,
    "concdvae_baseline": 1864,
    "concdvae_finetuned": 1299,
    "crystalformer_baseline": 1083,
    "crystallm_baseline": 98,
    "crysjepa_base": 1764,
    "crysjepa_refined": 1543,
}


@dataclass(frozen=True)
class AnalysisV2MagneticBuildReport:
    standardized_rows: int
    descriptor_v2_rows: int
    output_rows: int
    standardized_columns: int
    descriptor_v2_columns: int
    output_columns: int
    output_path: Path


def read_csv_table(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _require_columns(
    *,
    fieldnames: Sequence[str],
    required: Sequence[str],
    table_name: str,
) -> None:
    missing = [field for field in required if field not in fieldnames]
    if missing:
        raise RuntimeError(f"{table_name} missing required columns: {missing}")


def _validate_identity(
    rows: Sequence[Mapping[str, str]],
    *,
    table_name: str,
) -> None:
    structure_ids: list[str] = []
    sample_uids: list[str] = []

    for index, row in enumerate(rows, start=2):
        structure_id = str(row.get("structure_id") or "")
        sample_uid = str(row.get("sample_uid") or "")
        if not structure_id:
            raise RuntimeError(f"{table_name} row {index}: empty structure_id")
        if not sample_uid:
            raise RuntimeError(f"{table_name} row {index}: empty sample_uid")
        structure_ids.append(structure_id)
        sample_uids.append(sample_uid)

    duplicate_sample_uids = sorted(
        value for value, count in Counter(sample_uids).items() if count > 1
    )
    if duplicate_sample_uids:
        raise RuntimeError(
            f"{table_name}: duplicate sample_uid values: "
            f"{duplicate_sample_uids[:10]}"
        )

    duplicate_structure_ids = sorted(
        value for value, count in Counter(structure_ids).items() if count > 1
    )
    if duplicate_structure_ids:
        raise RuntimeError(
            f"{table_name}: duplicate structure_id values: "
            f"{duplicate_structure_ids[:10]}"
        )

    for index, row in enumerate(rows, start=2):
        structure_id = str(row.get("structure_id") or "")
        sample_uid = str(row.get("sample_uid") or "")
        if sample_uid != structure_id:
            raise RuntimeError(
                f"{table_name} row {index}: sample_uid != structure_id "
                f"({sample_uid!r} != {structure_id!r})"
            )


def _require_expected_count(
    *,
    actual: int,
    expected: int | None,
    label: str,
) -> None:
    if expected is not None and actual != expected:
        raise RuntimeError(f"{label}: expected {expected}, got {actual}")


def _require_cohort_counts(
    rows: Sequence[Mapping[str, str]],
    *,
    expected: Mapping[str, int] | None,
    table_name: str,
) -> None:
    if expected is None:
        return

    actual = Counter(str(row.get("analysis_cohort") or "") for row in rows)
    if dict(actual) != dict(expected):
        raise RuntimeError(
            f"{table_name} analysis_cohort counts differ: "
            f"expected={dict(expected)}, actual={dict(actual)}"
        )


def _descriptor_index(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    return {str(row["structure_id"]): row for row in rows}


def build_analysis_v2_magnetic(
    *,
    standardized_enrichment_path: str | Path = STANDARDIZED_ENRICHMENT_PATH,
    descriptor_v2_path: str | Path = DESCRIPTOR_V2_MAGNETIC_PATH,
    output_path: str | Path = DEFAULT_ANALYSIS_V2_MAGNETIC_OUTPUT_PATH,
    expected_rows: int | None = EXPECTED_ANALYSIS_V2_ROWS,
    expected_standardized_columns: int | None = EXPECTED_STANDARDIZED_COLUMNS,
    expected_descriptor_v2_columns: int | None = EXPECTED_DESCRIPTOR_V2_COLUMNS,
    expected_output_columns: int | None = EXPECTED_ANALYSIS_V2_COLUMNS,
    expected_cohort_counts: Mapping[str, int] | None = (
        EXPECTED_ANALYSIS_V2_COHORT_COUNTS
    ),
) -> AnalysisV2MagneticBuildReport:
    std_fields, std_rows = read_csv_table(standardized_enrichment_path)
    desc_fields, desc_rows = read_csv_table(descriptor_v2_path)

    _require_columns(
        fieldnames=std_fields,
        required=OVERLAPPING_IDENTITY_FIELDS,
        table_name="standardized enrichment",
    )
    _require_columns(
        fieldnames=desc_fields,
        required=OVERLAPPING_IDENTITY_FIELDS,
        table_name="Descriptor v2",
    )

    overlap = tuple(field for field in std_fields if field in desc_fields)
    if overlap != OVERLAPPING_IDENTITY_FIELDS:
        raise RuntimeError(
            "Input column overlap differs from Analysis v2 contract: "
            f"{overlap}"
        )

    _require_expected_count(
        actual=len(std_rows),
        expected=expected_rows,
        label="standardized enrichment rows",
    )
    _require_expected_count(
        actual=len(desc_rows),
        expected=expected_rows,
        label="Descriptor v2 rows",
    )
    _require_expected_count(
        actual=len(std_fields),
        expected=expected_standardized_columns,
        label="standardized enrichment columns",
    )
    _require_expected_count(
        actual=len(desc_fields),
        expected=expected_descriptor_v2_columns,
        label="Descriptor v2 columns",
    )

    _validate_identity(std_rows, table_name="standardized enrichment")
    _validate_identity(desc_rows, table_name="Descriptor v2")
    _require_cohort_counts(
        std_rows,
        expected=expected_cohort_counts,
        table_name="standardized enrichment",
    )
    _require_cohort_counts(
        desc_rows,
        expected=expected_cohort_counts,
        table_name="Descriptor v2",
    )

    std_ids = {str(row["structure_id"]) for row in std_rows}
    desc_ids = {str(row["structure_id"]) for row in desc_rows}
    if std_ids != desc_ids:
        missing_in_descriptor = sorted(std_ids - desc_ids)
        extra_in_descriptor = sorted(desc_ids - std_ids)
        raise RuntimeError(
            "Input structure_id sets differ: "
            f"missing_in_descriptor={missing_in_descriptor[:10]}, "
            f"extra_in_descriptor={extra_in_descriptor[:10]}"
        )

    std_sample_uids = {str(row["sample_uid"]) for row in std_rows}
    desc_sample_uids = {str(row["sample_uid"]) for row in desc_rows}
    if std_sample_uids != desc_sample_uids:
        raise RuntimeError("Input sample_uid sets differ")

    descriptor_specific_fields = [
        field for field in desc_fields if field not in OVERLAPPING_IDENTITY_FIELDS
    ]
    output_fields = [*std_fields, *descriptor_specific_fields]
    _require_expected_count(
        actual=len(output_fields),
        expected=expected_output_columns,
        label="Analysis v2 output columns",
    )

    descriptor_by_id = _descriptor_index(desc_rows)
    output_rows: list[dict[str, str]] = []

    for std_row in std_rows:
        structure_id = str(std_row["structure_id"])
        desc_row = descriptor_by_id[structure_id]

        mismatches = [
            field
            for field in OVERLAPPING_IDENTITY_FIELDS
            if str(std_row.get(field) or "") != str(desc_row.get(field) or "")
        ]
        if mismatches:
            raise RuntimeError(
                f"{structure_id}: overlapping identity fields differ: "
                f"{mismatches}"
            )

        output_row = {field: std_row.get(field, "") for field in std_fields}
        output_row.update(
            {
                field: desc_row.get(field, "")
                for field in descriptor_specific_fields
            }
        )
        output_rows.append(output_row)

    _require_expected_count(
        actual=len(output_rows),
        expected=expected_rows,
        label="Analysis v2 output rows",
    )
    _require_cohort_counts(
        output_rows,
        expected=expected_cohort_counts,
        table_name="Analysis v2 output",
    )

    written = write_stage_csv_atomic(output_path, output_rows, output_fields)

    return AnalysisV2MagneticBuildReport(
        standardized_rows=len(std_rows),
        descriptor_v2_rows=len(desc_rows),
        output_rows=len(output_rows),
        standardized_columns=len(std_fields),
        descriptor_v2_columns=len(desc_fields),
        output_columns=len(output_fields),
        output_path=written,
    )
