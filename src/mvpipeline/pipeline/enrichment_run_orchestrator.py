from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


CHECKS_MODULE = "mvpipeline.pipeline.enrichment_run_checks"
CHGNET_SCRIPT = "scripts/enrichment/run_batch_chgnet.py"
DXMAG_SCRIPT = "scripts/enrichment/run_batch_dxmag.py"
JOIN_SCRIPT = "scripts/enrichment/run_batch_join.py"


@dataclass(frozen=True)
class EnrichmentCohortRun:
    name: str
    expected_count: int
    manifest: str
    energy_output: str
    magnetism_output: str
    joined_output: str
    chgnet_label: str
    dxmag_label: str
    join_label: str


@dataclass(frozen=True)
class EnrichmentRunConfig:
    repo_root: Path
    energy_python: str
    magnetism_python: str
    checkpoint_every: int
    cohorts: tuple[EnrichmentCohortRun, ...]
    preflight_pass_label: str
    final_pass_label: str
    require_energy_ok: bool = False
    require_magnetism_ok: bool = False


@dataclass(frozen=True)
class EnrichmentCommand:
    label: str
    argv: tuple[str, ...]


def build_preflight_command(
    config: EnrichmentRunConfig,
) -> EnrichmentCommand:
    argv: list[str] = [
        config.magnetism_python,
        "-m",
        CHECKS_MODULE,
        "preflight",
    ]
    for cohort in config.cohorts:
        argv.extend(
            [
                "--manifest",
                cohort.manifest,
                str(cohort.expected_count),
            ]
        )
    argv.extend(
        [
            "--pass-label",
            config.preflight_pass_label,
        ]
    )
    return EnrichmentCommand("Pre-flight", tuple(argv))


def build_chgnet_command(
    cohort: EnrichmentCohortRun,
    config: EnrichmentRunConfig,
) -> EnrichmentCommand:
    return EnrichmentCommand(
        cohort.chgnet_label,
        (
            config.energy_python,
            CHGNET_SCRIPT,
            "--manifest",
            cohort.manifest,
            "--output",
            cohort.energy_output,
            "--resume",
            "--checkpoint-every",
            str(config.checkpoint_every),
        ),
    )


def build_dxmag_command(
    cohort: EnrichmentCohortRun,
    config: EnrichmentRunConfig,
) -> EnrichmentCommand:
    return EnrichmentCommand(
        cohort.dxmag_label,
        (
            config.magnetism_python,
            DXMAG_SCRIPT,
            "--manifest",
            cohort.manifest,
            "--output",
            cohort.magnetism_output,
            "--resume",
            "--checkpoint-every",
            str(config.checkpoint_every),
        ),
    )


def build_join_command(
    cohort: EnrichmentCohortRun,
    config: EnrichmentRunConfig,
) -> EnrichmentCommand:
    return EnrichmentCommand(
        cohort.join_label,
        (
            config.magnetism_python,
            JOIN_SCRIPT,
            "--annotations",
            cohort.manifest,
            "--energy",
            cohort.energy_output,
            "--magnetism",
            cohort.magnetism_output,
            "--output",
            cohort.joined_output,
        ),
    )


def build_final_audit_command(
    config: EnrichmentRunConfig,
) -> EnrichmentCommand:
    argv: list[str] = [
        config.magnetism_python,
        "-m",
        CHECKS_MODULE,
        "final-audit",
    ]
    for cohort in config.cohorts:
        argv.extend(
            [
                "--cohort",
                cohort.name,
                str(cohort.expected_count),
                cohort.manifest,
                cohort.energy_output,
                cohort.magnetism_output,
                cohort.joined_output,
            ]
        )
    if config.require_energy_ok:
        argv.append("--require-energy-ok")
    if config.require_magnetism_ok:
        argv.append("--require-magnetism-ok")
    argv.extend(
        [
            "--pass-label",
            config.final_pass_label,
        ]
    )
    return EnrichmentCommand("Final audit", tuple(argv))


def build_enrichment_commands(
    config: EnrichmentRunConfig,
) -> tuple[EnrichmentCommand, ...]:
    commands: list[EnrichmentCommand] = [
        build_preflight_command(config),
    ]
    commands.extend(
        build_chgnet_command(cohort, config)
        for cohort in config.cohorts
    )
    commands.extend(
        build_dxmag_command(cohort, config)
        for cohort in config.cohorts
    )
    commands.extend(
        build_join_command(cohort, config)
        for cohort in config.cohorts
    )
    commands.append(build_final_audit_command(config))
    return tuple(commands)


def print_section(label: str, *, leading_blank: bool = True) -> None:
    if leading_blank:
        print()
    print("============================================================")
    print(label)
    print("============================================================", flush=True)


def run_enrichment_commands(
    config: EnrichmentRunConfig,
    *,
    runner=subprocess.run,
) -> None:
    for index, command in enumerate(build_enrichment_commands(config)):
        print_section(command.label, leading_blank=index > 0)
        runner(
            list(command.argv),
            cwd=config.repo_root,
            check=True,
        )


def _parse_cohort_args(
    values: Sequence[Sequence[str]],
) -> tuple[EnrichmentCohortRun, ...]:
    return tuple(
        EnrichmentCohortRun(
            name=name,
            expected_count=int(expected_count),
            manifest=manifest,
            energy_output=energy_output,
            magnetism_output=magnetism_output,
            joined_output=joined_output,
            chgnet_label=chgnet_label,
            dxmag_label=dxmag_label,
            join_label=join_label,
        )
        for (
            name,
            expected_count,
            manifest,
            energy_output,
            magnetism_output,
            joined_output,
            chgnet_label,
            dxmag_label,
            join_label,
        ) in values
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run production enrichment stage commands."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--energy-python",
        required=True,
    )
    parser.add_argument(
        "--magnetism-python",
        required=True,
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
    )
    parser.add_argument(
        "--cohort",
        action="append",
        nargs=9,
        metavar=(
            "NAME",
            "EXPECTED_ROWS",
            "MANIFEST",
            "ENERGY",
            "MAGNETISM",
            "JOINED",
            "CHGNET_LABEL",
            "DXMAG_LABEL",
            "JOIN_LABEL",
        ),
        required=True,
    )
    parser.add_argument(
        "--preflight-pass-label",
        required=True,
    )
    parser.add_argument(
        "--final-pass-label",
        required=True,
    )
    parser.add_argument(
        "--require-energy-ok",
        action="store_true",
    )
    parser.add_argument(
        "--require-magnetism-ok",
        action="store_true",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> EnrichmentRunConfig:
    return EnrichmentRunConfig(
        repo_root=args.repo_root,
        energy_python=args.energy_python,
        magnetism_python=args.magnetism_python,
        checkpoint_every=args.checkpoint_every,
        cohorts=_parse_cohort_args(args.cohort),
        preflight_pass_label=args.preflight_pass_label,
        final_pass_label=args.final_pass_label,
        require_energy_ok=args.require_energy_ok,
        require_magnetism_ok=args.require_magnetism_ok,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run_enrichment_commands(config_from_args(args))


if __name__ == "__main__":
    main()
