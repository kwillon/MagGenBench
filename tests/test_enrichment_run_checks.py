import csv
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mvpipeline.pipeline.enrichment_run_checks import (
    CohortArtifactCheck,
    check_final_outputs,
    check_manifest_preflight,
)


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


def rows(*ids, status="ok"):
    return [
        {
            "structure_id": structure_id,
            "status": status,
        }
        for structure_id in ids
    ]


def manifest_rows(*ids):
    return [
        {
            "structure_id": structure_id,
        }
        for structure_id in ids
    ]


def write_artifacts(tmp_path, *, energy_status="ok", magnetism_status="ok"):
    annotations = tmp_path / "annotations.csv"
    energy = tmp_path / "energy.csv"
    magnetism = tmp_path / "magnetism.csv"
    joined = tmp_path / "joined.csv"

    write_csv(
        annotations,
        ["structure_id", "status"],
        rows("s1", "s2", status="accepted"),
    )
    write_csv(
        energy,
        ["structure_id", "status"],
        rows("s1", "s2", status=energy_status),
    )
    write_csv(
        magnetism,
        ["structure_id", "status"],
        rows("s1", "s2", status=magnetism_status),
    )
    write_csv(
        joined,
        ["structure_id", "status"],
        rows("s1", "s2", status="accepted"),
    )

    return annotations, energy, magnetism, joined


def cohort(tmp_path, **kwargs):
    annotations, energy, magnetism, joined = write_artifacts(
        tmp_path,
        energy_status=kwargs.pop("energy_status", "ok"),
        magnetism_status=kwargs.pop("magnetism_status", "ok"),
    )
    return CohortArtifactCheck(
        name="Example",
        expected_count=2,
        annotations=annotations,
        energy=energy,
        magnetism=magnetism,
        joined=joined,
        **kwargs,
    )


def test_correct_manifest_row_count_passes(tmp_path, capsys):
    manifest = tmp_path / "manifest.csv"
    write_csv(
        manifest,
        ["structure_id"],
        manifest_rows("s1", "s2"),
    )

    check_manifest_preflight(
        [(manifest, 2)],
        pass_label="PREFLIGHT: PASSED",
    )

    out = capsys.readouterr().out
    assert "rows: 2" in out
    assert "unique_structure_id: 2" in out
    assert "PREFLIGHT: PASSED" in out


def test_wrong_expected_manifest_count_fails(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_csv(
        manifest,
        ["structure_id"],
        manifest_rows("s1"),
    )

    with pytest.raises(RuntimeError, match="expected 2 rows, got 1"):
        check_manifest_preflight(
            [(manifest, 2)],
            pass_label="PREFLIGHT: PASSED",
        )


def test_empty_required_manifest_id_fails(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_csv(
        manifest,
        ["structure_id"],
        manifest_rows(""),
    )

    with pytest.raises(RuntimeError, match="empty structure_id"):
        check_manifest_preflight(
            [(manifest, 1)],
            pass_label="PREFLIGHT: PASSED",
        )


def test_duplicate_manifest_id_fails(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_csv(
        manifest,
        ["structure_id"],
        manifest_rows("s1", "s1"),
    )

    with pytest.raises(RuntimeError, match="duplicate structure_id"):
        check_manifest_preflight(
            [(manifest, 2)],
            pass_label="PREFLIGHT: PASSED",
        )


def test_correct_final_joined_row_count_passes(tmp_path, capsys):
    check_final_outputs(
        [cohort(tmp_path)],
        pass_label="FINAL: PASSED",
    )

    out = capsys.readouterr().out
    assert "joined_rows: 2" in out
    assert "unique_joined_structure_id: 2" in out
    assert "FINAL: PASSED" in out


def test_wrong_final_row_count_fails(tmp_path):
    spec = cohort(tmp_path)
    write_csv(
        spec.joined,
        ["structure_id", "status"],
        rows("s1"),
    )

    with pytest.raises(RuntimeError, match="joined expected 2 rows, got 1"):
        check_final_outputs(
            [spec],
            pass_label="FINAL: PASSED",
        )


def test_duplicate_output_ids_fail(tmp_path):
    spec = cohort(tmp_path)
    write_csv(
        spec.joined,
        ["structure_id", "status"],
        rows("s1", "s1"),
    )

    with pytest.raises(RuntimeError, match="duplicate joined structure_id"):
        check_final_outputs(
            [spec],
            pass_label="FINAL: PASSED",
        )


def test_all_required_status_ok_passes(tmp_path):
    check_final_outputs(
        [
            cohort(
                tmp_path,
                require_energy_ok=True,
                require_magnetism_ok=True,
            )
        ],
        pass_label="FINAL: PASSED",
    )


def test_non_ok_status_fails_only_when_required(tmp_path):
    relaxed = cohort(
        tmp_path / "relaxed",
        energy_status="error",
        magnetism_status="error",
    )
    check_final_outputs(
        [relaxed],
        pass_label="FINAL: PASSED",
    )

    strict = cohort(
        tmp_path / "strict",
        energy_status="error",
        require_energy_ok=True,
    )
    with pytest.raises(RuntimeError, match="non-success statuses"):
        check_final_outputs(
            [strict],
            pass_label="FINAL: PASSED",
        )


def test_no_final_id_set_comparison_is_added(tmp_path):
    spec = cohort(tmp_path)
    write_csv(
        spec.energy,
        ["structure_id", "status"],
        rows("other1", "other2"),
    )

    check_final_outputs(
        [spec],
        pass_label="FINAL: PASSED",
    )


def test_module_import_is_dependency_light():
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
        importlib.import_module(
            "mvpipeline.pipeline.enrichment_run_checks"
        )
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


def test_cli_exits_nonzero_on_validation_failure(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_csv(
        manifest,
        ["structure_id"],
        manifest_rows("s1"),
    )

    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mvpipeline.pipeline.enrichment_run_checks",
            "preflight",
            "--manifest",
            str(manifest),
            "2",
            "--pass-label",
            "PREFLIGHT: PASSED",
        ],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "expected 2 rows, got 1" in completed.stderr
