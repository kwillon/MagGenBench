from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from mvpipeline.analysis.cohorts import (
    EXPECTED_PRODUCTION_COHORT_COUNTS,
    EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS,
    EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS,
    EXPECTED_PRODUCTION_ROWS,
    production_analysis_cohort_specs,
)
from mvpipeline.analysis.unified import AnalysisCohortSpec, run_unified_analysis
from mvpipeline.io.stage_tables import read_stage_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unified analysis v1 production table.")
    parser.add_argument("--baseline-joined", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("runs/analysis_v1/unified_analysis_v1.csv"))
    return parser.parse_args()


def build_specs(args: argparse.Namespace) -> list[AnalysisCohortSpec]:
    return production_analysis_cohort_specs(
        baseline_joined_path=args.baseline_joined,
    )


def require_counter(rows, field: str, expected: dict[str, int]) -> None:
    actual = dict(Counter(row.get(field, "") for row in rows))
    if actual != expected:
        raise RuntimeError(f"{field} counts differ: expected={expected}, actual={actual}")


def main() -> None:
    args = parse_args()
    specs = build_specs(args)

    for spec in specs:
        for path in (spec.descriptor_path, spec.joined_path):
            if not path.is_file():
                raise FileNotFoundError(path)

    report = run_unified_analysis(cohorts=specs, output_path=args.output)
    rows = read_stage_csv(args.output)

    if (
        report.output_rows != EXPECTED_PRODUCTION_ROWS
        or len(rows) != EXPECTED_PRODUCTION_ROWS
    ):
        raise RuntimeError(
            f"Expected {EXPECTED_PRODUCTION_ROWS} rows, "
            f"got report={report.output_rows}, csv={len(rows)}"
        )

    require_counter(
        rows,
        "analysis_cohort",
        dict(EXPECTED_PRODUCTION_COHORT_COUNTS),
    )
    require_counter(
        rows,
        "descriptor_v1_status",
        dict(EXPECTED_PRODUCTION_DESCRIPTOR_STATUS_COUNTS),
    )
    require_counter(
        rows,
        "energy_status",
        dict(EXPECTED_PRODUCTION_ENERGY_STATUS_COUNTS),
    )
    require_counter(
        rows,
        "magnetism_status",
        dict(EXPECTED_PRODUCTION_MAGNETISM_STATUS_COUNTS),
    )

    print("===== Unified analysis v1 =====")
    print(report)
    print("analysis_cohort:", dict(Counter(row["analysis_cohort"] for row in rows)))
    print("analysis_family:", dict(Counter(row["analysis_family"] for row in rows)))
    print("analysis_state:", dict(Counter(row["analysis_state"] for row in rows)))
    print("descriptor_v1_status:", dict(Counter(row["descriptor_v1_status"] for row in rows)))
    print("energy_status:", dict(Counter(row["energy_status"] for row in rows)))
    print("magnetism_status:", dict(Counter(row["magnetism_status"] for row in rows)))
    print("UNIFIED_ANALYSIS_V1: PASSED")


if __name__ == "__main__":
    main()
