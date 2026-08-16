import os
import subprocess
import sys
import textwrap
from pathlib import Path

from mvpipeline.pipeline.enrichment_run_orchestrator import (
    CHGNET_SCRIPT,
    DXMAG_SCRIPT,
    JOIN_SCRIPT,
    EnrichmentCohortRun,
    EnrichmentRunConfig,
    build_chgnet_command,
    build_dxmag_command,
    build_enrichment_commands,
    build_final_audit_command,
    build_join_command,
    run_enrichment_commands,
)


def cohort(
    name="MatterGen-finetuned",
    expected_count=1376,
    manifest="tables/04_magnetic_screening/manifest.csv",
    energy="tables/06_energy/chgnet.csv",
    magnetism="tables/07_magnetic_descriptors/dxmag.csv",
    joined="tables/04_magnetic_screening/joined.csv",
):
    return EnrichmentCohortRun(
        name=name,
        expected_count=expected_count,
        manifest=manifest,
        energy_output=energy,
        magnetism_output=magnetism,
        joined_output=joined,
        chgnet_label=f"CHGNet - {name}",
        dxmag_label=f"DXMag - {name}",
        join_label=f"Join - {name}",
    )


def config(*cohorts, **kwargs):
    return EnrichmentRunConfig(
        repo_root=Path("/repo"),
        energy_python="/envs/energy/bin/python",
        magnetism_python="/envs/magnetism/bin/python",
        checkpoint_every=25,
        cohorts=tuple(cohorts) or (cohort(),),
        preflight_pass_label="PREFLIGHT: PASSED",
        final_pass_label="FINAL: PASSED",
        **kwargs,
    )


def test_chgnet_command_preserves_interpreter_script_and_resume():
    spec = cohort()
    command = build_chgnet_command(spec, config(spec))

    assert command.argv == (
        "/envs/energy/bin/python",
        CHGNET_SCRIPT,
        "--manifest",
        "tables/04_magnetic_screening/manifest.csv",
        "--output",
        "tables/06_energy/chgnet.csv",
        "--resume",
        "--checkpoint-every",
        "25",
    )


def test_dxmag_command_preserves_interpreter_script_and_resume():
    spec = cohort()
    command = build_dxmag_command(spec, config(spec))

    assert command.argv == (
        "/envs/magnetism/bin/python",
        DXMAG_SCRIPT,
        "--manifest",
        "tables/04_magnetic_screening/manifest.csv",
        "--output",
        "tables/07_magnetic_descriptors/dxmag.csv",
        "--resume",
        "--checkpoint-every",
        "25",
    )


def test_join_command_preserves_magnetism_interpreter_and_arguments():
    spec = cohort()
    command = build_join_command(spec, config(spec))

    assert command.argv == (
        "/envs/magnetism/bin/python",
        JOIN_SCRIPT,
        "--annotations",
        "tables/04_magnetic_screening/manifest.csv",
        "--energy",
        "tables/06_energy/chgnet.csv",
        "--magnetism",
        "tables/07_magnetic_descriptors/dxmag.csv",
        "--output",
        "tables/04_magnetic_screening/joined.csv",
    )


def test_orchestration_order_is_stage_grouped():
    first = cohort(name="first", expected_count=1)
    second = cohort(
        name="second",
        expected_count=2,
        manifest="m2.csv",
        energy="e2.csv",
        magnetism="d2.csv",
        joined="j2.csv",
    )

    commands = build_enrichment_commands(config(first, second))

    assert [command.label for command in commands] == [
        "Pre-flight",
        "CHGNet - first",
        "CHGNet - second",
        "DXMag - first",
        "DXMag - second",
        "Join - first",
        "Join - second",
        "Final audit",
    ]


def test_run_uses_check_true_and_repo_root_cwd():
    calls = []

    def runner(argv, *, cwd, check):
        calls.append((argv, cwd, check))

    cfg = config(cohort())

    run_enrichment_commands(cfg, runner=runner)

    assert calls
    assert {call[1] for call in calls} == {Path("/repo")}
    assert {call[2] for call in calls} == {True}


def test_finetuned_final_audit_does_not_add_strict_flags():
    command = build_final_audit_command(
        config(
            cohort(
                name="MatterGen-finetuned",
                expected_count=1376,
            ),
            cohort(
                name="Con-CDVAE-finetuned",
                expected_count=1299,
            ),
        )
    )

    assert "--require-energy-ok" not in command.argv
    assert "--require-magnetism-ok" not in command.argv
    assert "1376" in command.argv
    assert "1299" in command.argv


def test_crysjepa_final_audit_adds_strict_flags_and_counts():
    command = build_final_audit_command(
        config(
            cohort(name="Crys-JEPA-Base", expected_count=1764),
            cohort(name="Crys-JEPA-Refined", expected_count=1543),
            require_energy_ok=True,
            require_magnetism_ok=True,
        )
    )

    assert "--require-energy-ok" in command.argv
    assert "--require-magnetism-ok" in command.argv
    assert "1764" in command.argv
    assert "1543" in command.argv


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
            "mvpipeline.pipeline.enrichment_run_orchestrator"
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


def test_shell_wrappers_invoke_orchestrator_and_keep_defaults():
    repo_root = Path(__file__).resolve().parents[1]
    fine_tuned = (
        repo_root / "runs" / "enrichment" / "finetuned" / "run.sh"
    ).read_text(encoding="utf-8")
    crysjepa = (
        repo_root / "runs" / "enrichment" / "crysjepa" / "run.sh"
    ).read_text(encoding="utf-8")

    for text in (fine_tuned, crysjepa):
        assert "mvpipeline.pipeline.enrichment_run_orchestrator" in text
        assert '$ROOT/src:$ROOT/scripts/enrichment' in text
        assert '$ROOT/src:$ROOT/scripts/phase5a4' not in text
        assert (
            "MAGGENBENCH_ENERGY_PY:-"
            "/mnt/tank/scratch/kkapranova/envs/"
            "maggenbench-energy/bin/python"
        ) in text
        assert (
            "MAGGENBENCH_MAGNETISM_PY:-"
            "/mnt/tank/scratch/kkapranova/envs/"
            "maggenbench-magnetism/bin/python"
        ) in text
        assert "--checkpoint-every 25" in text
        assert "run_batch_chgnet.py \\" not in text
        assert "run_batch_dxmag.py \\" not in text
        assert "run_batch_join.py \\" not in text

    assert (
        "MAGGENBENCH_ROOT:-"
        "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench"
    ) in fine_tuned
    assert (
        '--cohort "MatterGen-finetuned" 1376'
    ) in fine_tuned
    assert (
        '--cohort "Con-CDVAE-finetuned" 1299'
    ) in fine_tuned
    assert "--require-energy-ok" not in fine_tuned
    assert "--require-magnetism-ok" not in fine_tuned

    assert (
        "MAGGENBENCH_ROOT:-"
        "/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa"
    ) in crysjepa
    assert '--cohort "Crys-JEPA-Base" 1764' in crysjepa
    assert '--cohort "Crys-JEPA-Refined" 1543' in crysjepa
    assert "--require-energy-ok" in crysjepa
    assert "--require-magnetism-ok" in crysjepa


def test_semantic_enrichment_run_paths_replace_old_active_paths():
    repo_root = Path(__file__).resolve().parents[1]
    new_paths = [
        repo_root / "runs" / "enrichment" / "finetuned" / "run.sh",
        repo_root / "runs" / "enrichment" / "crysjepa" / "run.sh",
    ]
    old_paths = [
        repo_root / "runs" / "phase5b_finetuned_enrichment",
        repo_root / "runs" / "crysjepa_enrichment",
    ]

    assert all(path.is_file() for path in new_paths)
    assert not any(path.exists() for path in old_paths)


def test_active_enrichment_scripts_use_semantic_path():
    repo_root = Path(__file__).resolve().parents[1]
    new_paths = [
        repo_root / "scripts" / "enrichment" / "run_batch_chgnet.py",
        repo_root / "scripts" / "enrichment" / "run_batch_dxmag.py",
        repo_root / "scripts" / "enrichment" / "run_batch_join.py",
        repo_root / "scripts" / "enrichment" / "batch_common.py",
    ]
    old_paths = [
        repo_root / "scripts" / "phase5a4" / "run_batch_chgnet.py",
        repo_root / "scripts" / "phase5a4" / "run_batch_dxmag.py",
        repo_root / "scripts" / "phase5a4" / "run_batch_join.py",
        repo_root / "scripts" / "phase5a4" / "batch_common.py",
    ]

    assert all(path.is_file() for path in new_paths)
    assert not any(path.exists() for path in old_paths)
    assert not (repo_root / "scripts" / "phase5a4").exists()
    assert (
        repo_root / "archive" / "scripts" / "phase5a4" / "prepare_batch_manifest.py"
    ).is_file()


def test_active_orchestration_no_longer_points_at_phase5a4_scripts():
    assert CHGNET_SCRIPT == "scripts/enrichment/run_batch_chgnet.py"
    assert DXMAG_SCRIPT == "scripts/enrichment/run_batch_dxmag.py"
    assert JOIN_SCRIPT == "scripts/enrichment/run_batch_join.py"

    active_values = [
        CHGNET_SCRIPT,
        DXMAG_SCRIPT,
        JOIN_SCRIPT,
    ]

    assert not any(
        "scripts/phase5a4/run_batch_" in value
        for value in active_values
    )
