from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .stage_common import require_all_status_ok


@dataclass(frozen=True)
class CohortArtifactCheck:
    name: str
    expected_count: int
    annotations: Path
    energy: Path
    magnetism: Path
    joined: Path
    require_energy_ok: bool = False
    require_magnetism_ok: bool = False


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def _require_expected_row_count(
    rows: Sequence[Mapping[str, str]],
    *,
    expected_count: int,
    label: str,
) -> None:
    if len(rows) != expected_count:
        raise RuntimeError(
            f"{label}: expected {expected_count} rows, got {len(rows)}"
        )


def _structure_ids(rows: Iterable[Mapping[str, str]]) -> list[str]:
    return [
        (row.get("structure_id") or "").strip()
        for row in rows
    ]


def check_manifest_preflight(
    manifests: Sequence[tuple[Path, int]],
    *,
    pass_label: str,
) -> None:
    for path, expected_rows in manifests:
        if not path.is_file():
            raise RuntimeError(f"Missing manifest: {path}")

        rows = read_csv_rows(path)
        ids = _structure_ids(rows)

        if len(rows) != expected_rows:
            raise RuntimeError(
                f"{path}: expected {expected_rows} rows, got {len(rows)}"
            )

        if len(ids) != len(set(ids)):
            raise RuntimeError(
                f"{path}: duplicate structure_id"
            )

        if any(not value for value in ids):
            raise RuntimeError(
                f"{path}: empty structure_id"
            )

        print(path)
        print("  rows:", len(rows))
        print("  unique_structure_id:", len(set(ids)))

    print(pass_label)


def check_final_outputs(
    cohorts: Sequence[CohortArtifactCheck],
    *,
    pass_label: str,
) -> None:
    for cohort in cohorts:
        print()
        print(cohort.name)

        for key in [
            "annotations",
            "energy",
            "magnetism",
            "joined",
        ]:
            path = getattr(cohort, key)

            if not path.is_file():
                raise RuntimeError(
                    f"{cohort.name}: missing {key}: {path}"
                )

            rows = read_csv_rows(path)

            print(f"  {key}_rows:", len(rows))

            if len(rows) != cohort.expected_count:
                raise RuntimeError(
                    f"{cohort.name}: {key} expected "
                    f"{cohort.expected_count} rows, got {len(rows)}"
                )

        energy = read_csv_rows(cohort.energy)
        magnetism = read_csv_rows(cohort.magnetism)
        joined = read_csv_rows(cohort.joined)

        energy_status = Counter(
            (row.get("status") or "").strip()
            for row in energy
        )

        magnetism_status = Counter(
            (row.get("status") or "").strip()
            for row in magnetism
        )

        if cohort.require_energy_ok:
            require_all_status_ok(
                energy,
                expected_count=cohort.expected_count,
                label=f"{cohort.name} energy",
            )

        if cohort.require_magnetism_ok:
            require_all_status_ok(
                magnetism,
                expected_count=cohort.expected_count,
                label=f"{cohort.name} magnetism",
            )

        joined_ids = _structure_ids(joined)

        print("  energy_status:", dict(energy_status))
        print("  magnetism_status:", dict(magnetism_status))
        print(
            "  unique_joined_structure_id:",
            len(set(joined_ids)),
        )

        if len(joined_ids) != len(set(joined_ids)):
            raise RuntimeError(
                f"{cohort.name}: duplicate joined structure_id"
            )

    print()
    print(pass_label)


def _parse_manifest_args(
    values: Sequence[Sequence[str]],
) -> list[tuple[Path, int]]:
    return [
        (Path(path), int(expected))
        for path, expected in values
    ]


def _parse_cohort_args(
    values: Sequence[Sequence[str]],
    *,
    require_energy_ok: bool,
    require_magnetism_ok: bool,
) -> list[CohortArtifactCheck]:
    return [
        CohortArtifactCheck(
            name=name,
            expected_count=int(expected),
            annotations=Path(annotations),
            energy=Path(energy),
            magnetism=Path(magnetism),
            joined=Path(joined),
            require_energy_ok=require_energy_ok,
            require_magnetism_ok=require_magnetism_ok,
        )
        for (
            name,
            expected,
            annotations,
            energy,
            magnetism,
            joined,
        ) in values
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate enrichment run CSV artifacts."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    preflight = subparsers.add_parser(
        "preflight",
        help="Validate manifest inputs before enrichment stages run.",
    )
    preflight.add_argument(
        "--manifest",
        action="append",
        nargs=2,
        metavar=("PATH", "EXPECTED_ROWS"),
        required=True,
    )
    preflight.add_argument(
        "--pass-label",
        required=True,
    )

    final = subparsers.add_parser(
        "final-audit",
        help="Validate final enrichment stage and joined outputs.",
    )
    final.add_argument(
        "--cohort",
        action="append",
        nargs=6,
        metavar=(
            "NAME",
            "EXPECTED_ROWS",
            "ANNOTATIONS",
            "ENERGY",
            "MAGNETISM",
            "JOINED",
        ),
        required=True,
    )
    final.add_argument(
        "--pass-label",
        required=True,
    )
    final.add_argument(
        "--require-energy-ok",
        action="store_true",
    )
    final.add_argument(
        "--require-magnetism-ok",
        action="store_true",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "preflight":
        check_manifest_preflight(
            _parse_manifest_args(args.manifest),
            pass_label=args.pass_label,
        )
        return

    if args.command == "final-audit":
        check_final_outputs(
            _parse_cohort_args(
                args.cohort,
                require_energy_ok=args.require_energy_ok,
                require_magnetism_ok=args.require_magnetism_ok,
            ),
            pass_label=args.pass_label,
        )
        return

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
