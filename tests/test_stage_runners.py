import csv
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mvpipeline.energy import EnergyResult, EnergyStatus
from mvpipeline.energy.backends.fake import FakeEnergyBackend
from mvpipeline.energy.records import ENERGY_RECORD_FIELDS
from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.magnetism import MagnetismResult, MagnetismStatus
from mvpipeline.magnetism.backends.fake import FakeMagnetismBackend
from mvpipeline.magnetism.records import MAGNETISM_RECORD_FIELDS
from mvpipeline.pipeline.energy_stage import run_energy_stage
from mvpipeline.pipeline.enrichment import run_enrichment
from mvpipeline.pipeline.magnetism_stage import run_magnetism_stage
from mvpipeline.pipeline.stage_common import (
    require_all_status_ok,
    success_ids_from_records,
)


def prepared_records():
    return [
        {
            "structure_id": "s1",
            "source_model": "generator-a",
            "source_path": "inputs/s1.cif",
            "run_id": "r1",
            "sample_id": "001",
            "structure": object(),
            "n_atoms": 2,
            "composition": {"Fe": 1, "O": 1},
            "features": [1.0, 2.0],
        },
        {
            "structure_id": "s2",
            "source_model": "generator-a",
            "source_path": "inputs/s2.cif",
            "run_id": "r1",
            "sample_id": "002",
            "structure": object(),
            "n_atoms": 3,
            "composition": {"Fe": 2, "O": 1},
            "features": [2.0, 3.0],
        },
    ]


def test_stage_modules_are_dependency_light():
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
        import mvpipeline
        importlib.import_module("mvpipeline.pipeline")
        importlib.import_module("mvpipeline.pipeline.energy_stage")
        importlib.import_module("mvpipeline.pipeline.magnetism_stage")
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


def test_energy_stage_with_fake_backend_preserves_order_and_provenance():
    report = run_energy_stage(prepared_records(), backend=FakeEnergyBackend())

    assert report.plan.stage_name == "energy"
    assert [row["structure_id"] for row in report.records] == ["s1", "s2"]
    assert [row["input_order"] for row in report.records] == [0, 1]
    assert report.records[0]["source_model"] == "generator-a"
    assert report.records[0]["source_path"] == "inputs/s1.cif"
    assert report.records[0]["status"] == "ok"
    assert report.records[0]["formation_energy_proxy_eV"] is not None
    assert "e_above_hull" not in report.records[0]


def test_magnetism_stage_with_fake_backend_keeps_scientific_names():
    report = run_magnetism_stage(prepared_records(), backend=FakeMagnetismBackend())
    row = report.records[0]

    assert row["structure_id"] == "s1"
    assert row["status"] == "ok"
    assert row["predicted_moment_value"] == 0.3
    assert row["moment_unit"] == "unknown"
    assert row["moment_normalization"] == "unknown"
    assert "uncertainty_proxy" in row
    assert "Ms" not in row
    assert "saturation_magnetization" not in row


def test_combined_fake_end_to_end_runs_both_stages_independently():
    report = run_enrichment(
        prepared_records(),
        energy_backend=FakeEnergyBackend(),
        magnetism_backend=FakeMagnetismBackend(),
    )

    assert report.energy is not None
    assert report.magnetism is not None
    assert [r["structure_id"] for r in report.energy.records] == ["s1", "s2"]
    assert [r["structure_id"] for r in report.magnetism.records] == ["s1", "s2"]


def test_empty_input_and_limit_none():
    report = run_energy_stage([], backend=FakeEnergyBackend(), limit=None)

    assert report.plan.input_count == 0
    assert report.plan.planned_count == 0
    assert report.records == []


def test_limit_zero_is_predictable_and_limit_applies_after_resume():
    report = run_energy_stage(
        prepared_records(),
        backend=FakeEnergyBackend(),
        limit=0,
        resume_success_ids={"s1"},
    )

    assert report.plan.input_count == 2
    assert report.plan.skipped_count == 1
    assert report.plan.planned_count == 0
    assert report.records == []


def test_negative_limit_is_invalid():
    with pytest.raises(ValueError, match="limit"):
        run_energy_stage(prepared_records(), backend=FakeEnergyBackend(), limit=-1)


def test_dry_run_does_not_call_backend_predict():
    class CountingBackend:
        name = "counting"
        model_name = "counting"

        def __init__(self):
            self.calls = 0

        def predict(self, item):
            self.calls += 1
            return EnergyResult(structure_id=item.structure_id, status=EnergyStatus.OK)

    backend = CountingBackend()
    report = run_energy_stage(prepared_records(), backend=backend, dry_run=True)

    assert backend.calls == 0
    assert report.plan.dry_run is True
    assert report.plan.planned_count == 2
    assert report.records == []


def test_injected_backend_takes_precedence_over_factory(monkeypatch):
    class InjectedBackend:
        name = "injected"
        model_name = "injected"

        def predict(self, item):
            return EnergyResult(
                structure_id=item.structure_id,
                status=EnergyStatus.OK,
                backend=self.name,
                model_name=self.model_name,
            )

    def forbidden_factory(config):
        raise AssertionError("factory should not be called")

    monkeypatch.setattr(
        "mvpipeline.pipeline.energy_stage.create_energy_backend", forbidden_factory
    )
    report = run_energy_stage(prepared_records(), backend=InjectedBackend())

    assert report.records[0]["backend"] == "injected"


def test_per_record_failure_is_isolated_by_default():
    records = prepared_records()
    records[0] = {k: v for k, v in records[0].items() if k != "n_atoms"}

    report = run_energy_stage(records, backend=FakeEnergyBackend())

    assert report.records[0]["status"] == "error"
    assert report.records[0]["error_code"] == "stage_record_error"
    assert report.records[1]["status"] == "ok"


def test_fail_fast_policy_raises_record_error():
    records = prepared_records()
    records[0] = {k: v for k, v in records[0].items() if k != "n_atoms"}

    with pytest.raises(ValueError, match="n_atoms"):
        run_energy_stage(records, backend=FakeEnergyBackend(), fail_fast=True)


def test_duplicate_structure_id_is_invalid():
    records = prepared_records()
    records[1] = {**records[1], "structure_id": "s1"}

    with pytest.raises(ValueError, match="Duplicate structure_id"):
        run_energy_stage(records, backend=FakeEnergyBackend())


def test_resume_skips_only_success_ids_and_failed_id_can_rerun():
    records = prepared_records()
    previous_results = [
        {"structure_id": "s1", "status": "ok"},
        {"structure_id": "s2", "status": "error"},
    ]
    report = run_energy_stage(
        records,
        backend=FakeEnergyBackend(),
        resume_success_ids=success_ids_from_records(previous_results),
    )

    assert [row["structure_id"] for row in report.records] == ["s2"]

    rerun = run_energy_stage(
        records,
        backend=FakeEnergyBackend(),
        resume_success_ids={"other-id"},
    )

    assert [row["structure_id"] for row in rerun.records] == ["s1", "s2"]


def test_resume_callback_skips_successful_ids():
    report = run_energy_stage(
        prepared_records(),
        backend=FakeEnergyBackend(),
        resume_success_predicate=lambda structure_id: structure_id == "s1",
    )

    assert [row["structure_id"] for row in report.records] == ["s2"]


def test_only_energy_only_magnetism_and_both_modes():
    energy_only = run_enrichment(
        prepared_records(),
        run_energy=True,
        run_magnetism=False,
        energy_backend=FakeEnergyBackend(),
    )
    magnetism_only = run_enrichment(
        prepared_records(),
        run_energy=False,
        run_magnetism=True,
        magnetism_backend=FakeMagnetismBackend(),
    )
    both = run_enrichment(
        prepared_records(),
        run_energy=True,
        run_magnetism=True,
        energy_backend=FakeEnergyBackend(),
        magnetism_backend=FakeMagnetismBackend(),
    )

    assert energy_only.energy is not None
    assert energy_only.magnetism is None
    assert magnetism_only.energy is None
    assert magnetism_only.magnetism is not None
    assert both.energy is not None
    assert both.magnetism is not None


def test_csv_serialization_atomic_empty_and_no_python_repr(tmp_path):
    path = tmp_path / "stage" / "energy.csv"
    rows = run_energy_stage(prepared_records(), backend=FakeEnergyBackend()).records
    fieldnames = [
        "structure_id",
        "input_order",
        "stage_name",
        "source_model",
        *ENERGY_RECORD_FIELDS,
    ]

    write_stage_csv_atomic(path, rows, fieldnames)

    text = path.read_text(encoding="utf-8")
    assert "object at 0x" not in text
    assert "e_above_hull" not in text
    with path.open(newline="", encoding="utf-8") as f:
        parsed = list(csv.DictReader(f))
    assert [row["structure_id"] for row in parsed] == ["s1", "s2"]
    assert not path.with_name(path.name + ".tmp").exists()

    empty_path = tmp_path / "stage" / "empty.csv"
    write_stage_csv_atomic(empty_path, [], ["structure_id", "status"])
    assert empty_path.read_text(encoding="utf-8").splitlines() == [
        "structure_id,status"
    ]


def test_atomic_output_does_not_replace_existing_file_on_bad_value(tmp_path):
    path = tmp_path / "stage.csv"
    path.write_text("old\n", encoding="utf-8")

    with pytest.raises(TypeError):
        write_stage_csv_atomic(path, [{"structure_id": object()}], ["structure_id"])

    assert path.read_text(encoding="utf-8") == "old\n"
    assert not path.with_name(path.name + ".tmp").exists()


def test_magnetism_csv_keeps_contract_field_names(tmp_path):
    path = tmp_path / "magnetism.csv"
    rows = run_magnetism_stage(
        prepared_records(), backend=FakeMagnetismBackend()
    ).records
    fieldnames = [
        "structure_id",
        "input_order",
        "stage_name",
        *MAGNETISM_RECORD_FIELDS,
    ]

    write_stage_csv_atomic(path, rows, fieldnames)

    text = path.read_text(encoding="utf-8")
    assert "predicted_moment_value" in text
    assert "uncertainty_proxy" in text
    assert "moment_unit" in text
    assert "moment_normalization" in text
    assert "saturation_magnetization" not in text
    assert "DFT magnetic moment" not in text


def test_require_all_status_ok_accepts_all_success():
    require_all_status_ok(
        [
            {"structure_id": "s1", "status": "ok"},
            {"structure_id": "s2", "status": "ok"},
        ],
        expected_count=2,
        label="energy",
    )


def test_require_all_status_ok_rejects_error_status():
    with pytest.raises(RuntimeError, match="non-success statuses"):
        require_all_status_ok(
            [
                {"structure_id": "s1", "status": "ok"},
                {"structure_id": "s2", "status": "error"},
            ],
            expected_count=2,
            label="magnetism",
        )


def test_require_all_status_ok_rejects_wrong_count():
    with pytest.raises(RuntimeError, match="expected 3 rows, got 2"):
        require_all_status_ok(
            [
                {"structure_id": "s1", "status": "ok"},
                {"structure_id": "s2", "status": "ok"},
            ],
            expected_count=3,
            label="energy",
        )
