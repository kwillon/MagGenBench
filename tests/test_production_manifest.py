import csv

import pytest

from mvpipeline.annotations.production_manifest import run_production_manifest


FIELDNAMES = [
    "sample_uid",
    "structure_id",
    "status",
    "cif_load_status",
    "cif_path",
    "extra",
]


def write_csv(path, rows, fieldnames=FIELDNAMES):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row(structure_id, status, load_status, cif_path, *, sample_uid=None, extra="x"):
    return {
        "sample_uid": structure_id if sample_uid is None else sample_uid,
        "structure_id": structure_id,
        "status": status,
        "cif_load_status": load_status,
        "cif_path": str(cif_path),
        "extra": extra,
    }


def test_production_manifest_filters_validated_loadable_rows_in_order(tmp_path):
    first_cif = tmp_path / "first.cif"
    second_cif = tmp_path / "second.cif"
    skipped_cif = tmp_path / "skipped.cif"
    for path in (first_cif, second_cif, skipped_cif):
        path.write_text("data\n", encoding="utf-8")

    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    write_csv(
        input_path,
        [
            row("s1", "validated", "ok", first_cif, extra="first"),
            row("skip-status", "rejected", "ok", skipped_cif),
            row("skip-load", "validated", "error", skipped_cif),
            row("s2", "validated", "ok_with_warnings", second_cif, extra="second"),
        ],
    )

    report = run_production_manifest(input_path=input_path, output_path=output_path)
    output = read_csv(output_path)

    assert report.input_rows == 4
    assert report.production_rows == 2
    assert [r["structure_id"] for r in output] == ["s1", "s2"]
    assert list(output[0]) == FIELDNAMES
    assert [r["extra"] for r in output] == ["first", "second"]


def test_production_manifest_rejects_empty_production_cohort(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data\n", encoding="utf-8")
    input_path = tmp_path / "input.csv"
    write_csv(input_path, [row("s1", "rejected", "ok", cif)])

    with pytest.raises(RuntimeError, match="Production cohort is empty."):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )


def test_production_manifest_rejects_missing_header(tmp_path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Input CSV has no header."):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )


def test_production_manifest_rejects_duplicate_structure_id(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data\n", encoding="utf-8")
    input_path = tmp_path / "input.csv"
    write_csv(
        input_path,
        [
            row("dup", "validated", "ok", cif),
            row("dup", "validated", "ok_with_warnings", cif),
        ],
    )

    with pytest.raises(RuntimeError, match="Duplicate structure_id"):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )


def test_production_manifest_rejects_sample_uid_mismatch(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data\n", encoding="utf-8")
    input_path = tmp_path / "input.csv"
    write_csv(
        input_path,
        [row("s1", "validated", "ok", cif, sample_uid="other")],
    )

    with pytest.raises(RuntimeError, match="sample_uid/structure_id mismatches: 1"):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )


def test_production_manifest_rejects_missing_cif(tmp_path):
    input_path = tmp_path / "input.csv"
    write_csv(
        input_path,
        [row("s1", "validated", "ok", tmp_path / "missing.cif")],
    )

    with pytest.raises(RuntimeError, match="Missing CIF files: 1"):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )


def test_production_manifest_rejects_empty_structure_id(tmp_path):
    cif = tmp_path / "sample.cif"
    cif.write_text("data\n", encoding="utf-8")
    input_path = tmp_path / "input.csv"
    write_csv(input_path, [row("", "validated", "ok", cif)])

    with pytest.raises(RuntimeError, match="Empty structure_id"):
        run_production_manifest(
            input_path=input_path,
            output_path=tmp_path / "output.csv",
        )
