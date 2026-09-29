from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


@dataclass(frozen=True)
class ValidationCohortConfig:
    key: str
    input_dir: Path
    out_dir: Path
    train_reference: Path
    thresholds: Path
    model_name: str
    refuse_existing_output: bool = False


MATTERGEN_FINETUNED_VALIDATION = ValidationCohortConfig(
    key="mattergen-finetuned",
    input_dir=Path("samples/mattergen_finetuned_cifs"),
    out_dir=Path("outputs/mattergen_finetuned"),
    train_reference=Path("datasets/mattergen/train_reference.csv"),
    thresholds=Path("config/thresholds.yaml"),
    model_name="MatterGen-finetuned",
)


CONCDVAE_FINETUNED_VALIDATION = ValidationCohortConfig(
    key="concdvae-finetuned",
    input_dir=Path("samples/concdvae_finetuned_cifs"),
    out_dir=Path("outputs/concdvae_finetuned"),
    train_reference=Path("datasets/mattergen/train_reference.csv"),
    thresholds=Path("config/thresholds.yaml"),
    model_name="Con-CDVAE-finetuned",
)


CRYSTALLM_FINETUNED_VALIDATION = ValidationCohortConfig(
    key="crystallm-finetuned",
    input_dir=Path("samples/crystallm_finetuned_cifs"),
    out_dir=Path("outputs/crystallm_finetuned"),
    train_reference=Path("datasets/mattergen/train_reference.csv"),
    thresholds=Path("config/thresholds.yaml"),
    model_name="CrystaLLM-finetuned",
    refuse_existing_output=True,
)


CRYSJEPA_BASE_VALIDATION = ValidationCohortConfig(
    key="crysjepa-base",
    input_dir=Path("samples/crysjepa_base_cifs"),
    out_dir=Path("outputs/crysjepa_base"),
    train_reference=Path("datasets/mattergen/train_reference.csv"),
    thresholds=Path("config/thresholds.yaml"),
    model_name="Crys-JEPA-Base",
    refuse_existing_output=True,
)


CRYSJEPA_REFINED_VALIDATION = ValidationCohortConfig(
    key="crysjepa-refined",
    input_dir=Path("samples/crysjepa_refined_cifs"),
    out_dir=Path("outputs/crysjepa_refined"),
    train_reference=Path("datasets/mattergen/train_reference.csv"),
    thresholds=Path("config/thresholds.yaml"),
    model_name="Crys-JEPA-Refined",
    refuse_existing_output=True,
)


VALIDATION_COHORTS = {
    MATTERGEN_FINETUNED_VALIDATION.key: MATTERGEN_FINETUNED_VALIDATION,
    CONCDVAE_FINETUNED_VALIDATION.key: CONCDVAE_FINETUNED_VALIDATION,
    CRYSTALLM_FINETUNED_VALIDATION.key: CRYSTALLM_FINETUNED_VALIDATION,
    CRYSJEPA_BASE_VALIDATION.key: CRYSJEPA_BASE_VALIDATION,
    CRYSJEPA_REFINED_VALIDATION.key: CRYSJEPA_REFINED_VALIDATION,
}


def get_validation_cohort(key: str) -> ValidationCohortConfig:
    try:
        return VALIDATION_COHORTS[key]
    except KeyError as exc:
        choices = ", ".join(sorted(VALIDATION_COHORTS))
        raise ValueError(f"Unknown validation cohort {key!r}; choose one of: {choices}") from exc


def build_validation_argv(
    cohort: ValidationCohortConfig,
    *,
    mvp_executable: str,
) -> tuple[str, ...]:
    return (
        mvp_executable,
        "--input-dir",
        str(cohort.input_dir),
        "--out-dir",
        str(cohort.out_dir),
        "--train-reference",
        str(cohort.train_reference),
        "--thresholds",
        str(cohort.thresholds),
        "--model-name",
        cohort.model_name,
        "--no-pretty",
    )


def validation_environment(
    *,
    repo_root: Path,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env["PYTHONPATH"] = str(repo_root / "src")
    return env


def check_output_guard(
    cohort: ValidationCohortConfig,
    *,
    repo_root: Path,
) -> None:
    if cohort.refuse_existing_output and (repo_root / cohort.out_dir).exists():
        raise RuntimeError(f"Refusing to overwrite {cohort.out_dir}")


def run_validation_command(
    cohort: ValidationCohortConfig,
    *,
    repo_root: Path,
    mvp_executable: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> subprocess.CompletedProcess:
    check_output_guard(cohort, repo_root=repo_root)
    return runner(
        build_validation_argv(cohort, mvp_executable=mvp_executable),
        cwd=repo_root,
        env=validation_environment(repo_root=repo_root),
        check=True,
    )
