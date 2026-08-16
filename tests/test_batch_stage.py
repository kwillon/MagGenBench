from __future__ import annotations

import csv
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.pipeline.batch_stage import (
    load_previous_stage_results,
    run_checkpointed_batch,
)
from mvpipeline.pipeline.stage_common import PreparedStructureRecord


FIELDS = ("structure_id", "status", "value")


def prepared(*ids: str) -> list[PreparedStructureRecord]:
    return [
        PreparedStructureRecord(structure_id=structure_id, order=order)
        for order, structure_id in enumerate(ids)
    ]


def row(structure_id: str, status: str = "ok", value: str = "") -> dict[str, str]:
    return {
        "structure_id": structure_id,
        "status": status,
        "value": value or structure_id,
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_resume_loader_reads_existing_output_when_resuming(tmp_path: Path) -> None:
    output = tmp_path / "stage.csv"
    write_stage_csv_atomic(output, [row("s1")], FIELDS)

    rows = load_previous_stage_results(
        resume=True,
        output_path=output,
    )

    assert rows == [row("s1")]


def test_resume_loader_ignores_existing_output_when_not_resuming(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stage.csv"
    write_stage_csv_atomic(output, [row("s1")], FIELDS)

    rows = load_previous_stage_results(
        resume=False,
        output_path=output,
    )

    assert rows == []


def test_resume_loader_returns_empty_for_missing_output(tmp_path: Path) -> None:
    rows = load_previous_stage_results(
        resume=True,
        output_path=tmp_path / "missing.csv",
    )

    assert rows == []


def test_batch_stage_module_is_dependency_light() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import importlib
        import sys

        blocked = {
            "pymatgen",
            "yaml",
            "matgl",
            "chgnet",
            "torch",
            "numpy",
            "pandas",
            "matminer",
            "sklearn",
            "joblib",
        }
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            if level == 0 and root in blocked:
                raise AssertionError(f"{name} must not be imported")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        importlib.import_module("mvpipeline.pipeline.batch_stage")
        assert not [m for m in sys.modules if m.split(".", 1)[0] in blocked]
        """
    )
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_fresh_run_writes_all_rows_in_input_order(tmp_path: Path) -> None:
    output = tmp_path / "stage.csv"

    report = run_checkpointed_batch(
        prepared_records=prepared("s1", "s2"),
        output_path=output,
        fieldnames=FIELDS,
        checkpoint_every=25,
        previous_results=[],
        run_chunk=lambda chunk: [row(record.structure_id) for record in chunk],
    )

    assert [record["structure_id"] for record in report.records] == ["s1", "s2"]
    assert [record["structure_id"] for record in read_rows(output)] == ["s1", "s2"]
    assert report.new_result_count == 2
    assert report.checkpoint_count == 1
    assert not output.with_name(output.name + ".tmp").exists()


def test_checkpointing_writes_after_each_chunk(tmp_path: Path) -> None:
    output = tmp_path / "stage.csv"
    snapshots: list[list[str]] = []

    def run_chunk(chunk):
        if output.exists():
            snapshots.append([record["structure_id"] for record in read_rows(output)])
        return [row(record.structure_id) for record in chunk]

    report = run_checkpointed_batch(
        prepared_records=prepared("s1", "s2", "s3"),
        output_path=output,
        fieldnames=FIELDS,
        checkpoint_every=1,
        previous_results=[],
        run_chunk=run_chunk,
    )

    assert snapshots == [["s1"], ["s1", "s2"]]
    assert [record["structure_id"] for record in read_rows(output)] == [
        "s1",
        "s2",
        "s3",
    ]
    assert report.checkpoint_count == 3


def test_resume_skips_successful_rows_and_reruns_failed_rows(tmp_path: Path) -> None:
    output = tmp_path / "stage.csv"
    write_stage_csv_atomic(
        output,
        [row("s1", "ok", "old-ok"), row("s2", "error", "old-error")],
        FIELDS,
    )
    seen_chunks: list[list[str]] = []

    def run_chunk(chunk):
        seen_chunks.append([record.structure_id for record in chunk])
        return [row(record.structure_id, "ok", "rerun") for record in chunk]

    report = run_checkpointed_batch(
        prepared_records=prepared("s1", "s2", "s3"),
        output_path=output,
        fieldnames=FIELDS,
        checkpoint_every=25,
        previous_results=load_previous_stage_results(
            resume=True,
            output_path=output,
        ),
        run_chunk=run_chunk,
    )

    assert seen_chunks == [["s2", "s3"]]
    assert len(report.resume_success_ids) == 1
    assert [record["value"] for record in read_rows(output)] == [
        "old-ok",
        "rerun",
        "rerun",
    ]


def test_zero_pending_resume_rewrites_unchanged_successful_result(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stage.csv"
    write_stage_csv_atomic(output, [row("s1"), row("s2")], FIELDS)

    report = run_checkpointed_batch(
        prepared_records=prepared("s1", "s2"),
        output_path=output,
        fieldnames=FIELDS,
        checkpoint_every=25,
        previous_results=load_previous_stage_results(
            resume=True,
            output_path=output,
        ),
        run_chunk=lambda chunk: pytest.fail("no chunk should run"),
    )

    assert report.pending_records == []
    assert report.new_result_count == 0
    assert report.checkpoint_count == 0
    assert [record["structure_id"] for record in read_rows(output)] == ["s1", "s2"]


def test_invalid_checkpoint_size_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="checkpoint-every"):
        run_checkpointed_batch(
            prepared_records=prepared("s1"),
            output_path=tmp_path / "stage.csv",
            fieldnames=FIELDS,
            checkpoint_every=0,
            previous_results=[],
            run_chunk=lambda chunk: [],
        )


def test_duplicate_prepared_ids_fail(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Duplicate structure_id"):
        run_checkpointed_batch(
            prepared_records=prepared("s1", "s1"),
            output_path=tmp_path / "stage.csv",
            fieldnames=FIELDS,
            checkpoint_every=25,
            previous_results=[],
            run_chunk=lambda chunk: [],
        )


def test_unknown_previous_id_fails(tmp_path: Path) -> None:
    output = tmp_path / "stage.csv"
    write_stage_csv_atomic(output, [row("outside")], FIELDS)

    with pytest.raises(ValueError, match="Unexpected structure_id"):
        run_checkpointed_batch(
            prepared_records=prepared("s1"),
            output_path=output,
            fieldnames=FIELDS,
            checkpoint_every=25,
            previous_results=load_previous_stage_results(
                resume=True,
                output_path=output,
            ),
            run_chunk=lambda chunk: [],
        )


def test_missing_final_rows_fail_without_marking_unprocessed_successful(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stage.csv"

    with pytest.raises(RuntimeError, match="Expected 2 final results"):
        run_checkpointed_batch(
            prepared_records=prepared("s1", "s2"),
            output_path=output,
            fieldnames=FIELDS,
            checkpoint_every=25,
            previous_results=[],
            run_chunk=lambda chunk: [row("s1")],
        )

    assert [record["structure_id"] for record in read_rows(output)] == ["s1"]


def test_stage_exception_does_not_write_current_failed_chunk(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stage.csv"

    def run_chunk(chunk):
        if chunk[0].structure_id == "s2":
            raise RuntimeError("stage failed")
        return [row(record.structure_id) for record in chunk]

    with pytest.raises(RuntimeError, match="stage failed"):
        run_checkpointed_batch(
            prepared_records=prepared("s1", "s2"),
            output_path=output,
            fieldnames=FIELDS,
            checkpoint_every=1,
            previous_results=[],
            run_chunk=run_chunk,
        )

    assert [record["structure_id"] for record in read_rows(output)] == ["s1"]
