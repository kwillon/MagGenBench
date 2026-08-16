from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


LOADABLE_STATUSES = {
    "ok",
    "ok_with_warnings",
}


@dataclass(frozen=True)
class ProductionManifestReport:
    input_rows: int
    production_rows: int
    unique_structure_ids: int
    sample_uid_mismatch: int
    missing_cif: int
    output_path: Path


def read_manifest_csv(path: Path) -> tuple[list[str] | None, list[dict[str, str]]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    return fieldnames, rows


def select_production_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[Mapping[str, str]]:
    return [
        r
        for r in rows
        if r.get("status") == "validated"
        and r.get("cif_load_status") in LOADABLE_STATUSES
    ]


def validate_production_rows(rows: Sequence[Mapping[str, str]]) -> None:
    ids = [r.get("structure_id", "") for r in rows]

    if not rows:
        raise RuntimeError("Production cohort is empty.")

    if any(not sid for sid in ids):
        raise RuntimeError("Empty structure_id in production cohort.")

    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate structure_id in production cohort.")

    uid_mismatches = [
        r for r in rows if r.get("sample_uid") != r.get("structure_id")
    ]

    if uid_mismatches:
        raise RuntimeError(
            f"sample_uid/structure_id mismatches: {len(uid_mismatches)}"
        )

    missing_cifs = [
        r for r in rows if not Path(r.get("cif_path", "")).is_file()
    ]

    if missing_cifs:
        raise RuntimeError(f"Missing CIF files: {len(missing_cifs)}")


def write_production_manifest(
    rows: Sequence[Mapping[str, str]],
    *,
    fieldnames: Sequence[str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def run_production_manifest(
    *,
    input_path: Path,
    output_path: Path,
) -> ProductionManifestReport:
    fieldnames, rows = read_manifest_csv(input_path)

    if not fieldnames:
        raise RuntimeError("Input CSV has no header.")

    selected = select_production_rows(rows)
    validate_production_rows(selected)
    write_production_manifest(
        selected,
        fieldnames=fieldnames,
        output_path=output_path,
    )

    ids = [r.get("structure_id", "") for r in selected]
    uid_mismatches = [
        r for r in selected if r.get("sample_uid") != r.get("structure_id")
    ]
    missing_cifs = [
        r for r in selected if not Path(r.get("cif_path", "")).is_file()
    ]

    report = ProductionManifestReport(
        input_rows=len(rows),
        production_rows=len(selected),
        unique_structure_ids=len(set(ids)),
        sample_uid_mismatch=len(uid_mismatches),
        missing_cif=len(missing_cifs),
        output_path=output_path,
    )

    print("input_rows:", report.input_rows)
    print("production_rows:", report.production_rows)
    print("unique_structure_ids:", report.unique_structure_ids)
    print("sample_uid_mismatch:", report.sample_uid_mismatch)
    print("missing_cif:", report.missing_cif)
    print("output:", report.output_path)
    print("PHASE5A6_PRODUCTION_MANIFEST: PASSED")

    return report

