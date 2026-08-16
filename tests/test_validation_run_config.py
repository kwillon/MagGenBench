from pathlib import Path

import pytest

from mvpipeline.validation.run_config import (
    CONCDVAE_FINETUNED_VALIDATION,
    CRYSJEPA_BASE_VALIDATION,
    CRYSJEPA_REFINED_VALIDATION,
    MATTERGEN_FINETUNED_VALIDATION,
    VALIDATION_COHORTS,
    build_validation_argv,
    get_validation_cohort,
    run_validation_command,
    validation_environment,
)


MVP = "/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp"
MAIN_ROOT = "/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench"
CRYSJEPA_ROOT = "/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa"


EXPECTED_ARGV = {
    "mattergen-finetuned": (
        MVP,
        "--input-dir",
        "samples/mattergen_finetuned_cifs",
        "--out-dir",
        "outputs/mattergen_finetuned",
        "--train-reference",
        "datasets/mattergen/train_reference.csv",
        "--thresholds",
        "config/thresholds.yaml",
        "--model-name",
        "MatterGen-finetuned",
        "--no-pretty",
    ),
    "concdvae-finetuned": (
        MVP,
        "--input-dir",
        "samples/concdvae_finetuned_cifs",
        "--out-dir",
        "outputs/concdvae_finetuned",
        "--train-reference",
        "datasets/mattergen/train_reference.csv",
        "--thresholds",
        "config/thresholds.yaml",
        "--model-name",
        "Con-CDVAE-finetuned",
        "--no-pretty",
    ),
    "crysjepa-base": (
        MVP,
        "--input-dir",
        "samples/crysjepa_base_cifs",
        "--out-dir",
        "outputs/crysjepa_base",
        "--train-reference",
        "datasets/mattergen/train_reference.csv",
        "--thresholds",
        "config/thresholds.yaml",
        "--model-name",
        "Crys-JEPA-Base",
        "--no-pretty",
    ),
    "crysjepa-refined": (
        MVP,
        "--input-dir",
        "samples/crysjepa_refined_cifs",
        "--out-dir",
        "outputs/crysjepa_refined",
        "--train-reference",
        "datasets/mattergen/train_reference.csv",
        "--thresholds",
        "config/thresholds.yaml",
        "--model-name",
        "Crys-JEPA-Refined",
        "--no-pretty",
    ),
}


def wrapper_text(path):
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / path).read_text(encoding="utf-8")


def test_validation_cohort_registry_is_exact():
    assert tuple(VALIDATION_COHORTS) == (
        "mattergen-finetuned",
        "concdvae-finetuned",
        "crysjepa-base",
        "crysjepa-refined",
    )

    assert VALIDATION_COHORTS["mattergen-finetuned"] is MATTERGEN_FINETUNED_VALIDATION
    assert VALIDATION_COHORTS["concdvae-finetuned"] is CONCDVAE_FINETUNED_VALIDATION
    assert VALIDATION_COHORTS["crysjepa-base"] is CRYSJEPA_BASE_VALIDATION
    assert VALIDATION_COHORTS["crysjepa-refined"] is CRYSJEPA_REFINED_VALIDATION


def test_validation_cohort_configurations_preserve_current_paths_and_models():
    assert MATTERGEN_FINETUNED_VALIDATION.input_dir == Path(
        "samples/mattergen_finetuned_cifs"
    )
    assert MATTERGEN_FINETUNED_VALIDATION.out_dir == Path(
        "outputs/mattergen_finetuned"
    )
    assert MATTERGEN_FINETUNED_VALIDATION.model_name == "MatterGen-finetuned"
    assert MATTERGEN_FINETUNED_VALIDATION.refuse_existing_output is False

    assert CONCDVAE_FINETUNED_VALIDATION.input_dir == Path(
        "samples/concdvae_finetuned_cifs"
    )
    assert CONCDVAE_FINETUNED_VALIDATION.out_dir == Path(
        "outputs/concdvae_finetuned"
    )
    assert CONCDVAE_FINETUNED_VALIDATION.model_name == "Con-CDVAE-finetuned"
    assert CONCDVAE_FINETUNED_VALIDATION.refuse_existing_output is False

    assert CRYSJEPA_BASE_VALIDATION.input_dir == Path("samples/crysjepa_base_cifs")
    assert CRYSJEPA_BASE_VALIDATION.out_dir == Path("outputs/crysjepa_base")
    assert CRYSJEPA_BASE_VALIDATION.model_name == "Crys-JEPA-Base"
    assert CRYSJEPA_BASE_VALIDATION.refuse_existing_output is True

    assert CRYSJEPA_REFINED_VALIDATION.input_dir == Path(
        "samples/crysjepa_refined_cifs"
    )
    assert CRYSJEPA_REFINED_VALIDATION.out_dir == Path("outputs/crysjepa_refined")
    assert CRYSJEPA_REFINED_VALIDATION.model_name == "Crys-JEPA-Refined"
    assert CRYSJEPA_REFINED_VALIDATION.refuse_existing_output is True

    for cohort in VALIDATION_COHORTS.values():
        assert cohort.train_reference == Path("datasets/mattergen/train_reference.csv")
        assert cohort.thresholds == Path("config/thresholds.yaml")


def test_validation_argv_matches_original_wrappers():
    for key, expected in EXPECTED_ARGV.items():
        assert (
            build_validation_argv(
                get_validation_cohort(key),
                mvp_executable=MVP,
            )
            == expected
        )


def test_run_validation_command_uses_cwd_env_check_true_and_runner():
    calls = []

    def runner(argv, *, cwd, env, check):
        calls.append((argv, cwd, env, check))
        return "completed"

    result = run_validation_command(
        MATTERGEN_FINETUNED_VALIDATION,
        repo_root=Path("/repo"),
        mvp_executable=MVP,
        runner=runner,
    )

    assert result == "completed"
    assert calls == [
        (
            EXPECTED_ARGV["mattergen-finetuned"],
            Path("/repo"),
            validation_environment(repo_root=Path("/repo")),
            True,
        )
    ]


def test_crysjepa_existing_output_guard_is_preserved(tmp_path):
    (tmp_path / "outputs" / "crysjepa_base").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="Refusing to overwrite outputs/crysjepa_base"):
        run_validation_command(
            CRYSJEPA_BASE_VALIDATION,
            repo_root=tmp_path,
            mvp_executable=MVP,
            runner=lambda *args, **kwargs: None,
        )


def test_wrapper_defaults_and_delegation_are_exact():
    wrappers = {
        "mattergen-finetuned": (
            "runs/phase5b_mattergen_finetuned_validation/run_validation.sh",
            MAIN_ROOT,
        ),
        "concdvae-finetuned": (
            "runs/phase5b_concdvae_finetuned_validation/run_validation.sh",
            MAIN_ROOT,
        ),
        "crysjepa-base": (
            "runs/crysjepa_base_validation/run_validation.sh",
            CRYSJEPA_ROOT,
        ),
        "crysjepa-refined": (
            "runs/crysjepa_refined_validation/run_validation.sh",
            CRYSJEPA_ROOT,
        ),
    }

    for cohort, (path, root) in wrappers.items():
        text = wrapper_text(path)
        assert f'REPO="${{MAGGENBENCH_ROOT:-{root}}}"' in text
        assert (
            'MVP="${MAGGENBENCH_MVP:-'
            '/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp}"'
        ) in text
        assert 'PY="${MAGGENBENCH_VALIDATION_PY:-${MVP%/mvp}/python}"' in text
        assert 'export PYTHONPATH="$REPO/src"' in text
        assert '"$PY" scripts/validation/run_validation.py \\' in text
        assert f"--cohort {cohort}" in text
        assert '--repo-root "$REPO"' in text
        assert '--mvp "$MVP"' in text
        assert '"$MVP" \\' not in text
        assert "--input-dir" not in text
        assert "--out-dir" not in text
        assert "--train-reference" not in text
        assert "--thresholds" not in text
        assert "--model-name" not in text

