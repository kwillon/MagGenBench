from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from mvpipeline.analysis.unified import AnalysisCohortSpec, run_unified_analysis
from mvpipeline.io.stage_tables import read_stage_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unified analysis v1 production table.")
    parser.add_argument("--baseline-joined", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("runs/analysis_v1/unified_analysis_v1.csv"))
    return parser.parse_args()


def build_specs(args: argparse.Namespace) -> list[AnalysisCohortSpec]:
    return [
        AnalysisCohortSpec("baseline_master", None, "baseline", Path("runs/descriptor_v1_full/baseline_master_descriptors_v1.csv"), args.baseline_joined),
        AnalysisCohortSpec("mattergen_finetuned", "MatterGen", "fine_tuned", Path("runs/descriptor_v1_full/mattergen_finetuned_descriptors_v1.csv"), Path("tables/04_magnetic_screening/phase5b_mattergen_finetuned_joined.csv")),
        AnalysisCohortSpec("concdvae_finetuned", "Con-CDVAE", "fine_tuned", Path("runs/descriptor_v1_full/concdvae_finetuned_descriptors_v1.csv"), Path("tables/04_magnetic_screening/phase5b_concdvae_finetuned_joined.csv")),
        AnalysisCohortSpec("crysjepa_base", "Crys-JEPA", "base", Path("runs/descriptor_v1_full/crysjepa_base_descriptors_v1.csv"), Path("tables/04_magnetic_screening/crysjepa_base_joined.csv")),
        AnalysisCohortSpec("crysjepa_refined", "Crys-JEPA", "refined", Path("runs/descriptor_v1_full/crysjepa_refined_descriptors_v1.csv"), Path("tables/04_magnetic_screening/crysjepa_refined_joined.csv")),
    ]


EXPECTED_ROWS = 10684
EXPECTED_COHORTS = {
    "baseline_master": 4702,
    "mattergen_finetuned": 1376,
    "concdvae_finetuned": 1299,
    "crysjepa_base": 1764,
    "crysjepa_refined": 1543,
}
EXPECTED_DESCRIPTOR_STATUS = {"ok": 10681, "partial": 3}
EXPECTED_ENERGY_STATUS = {"ok": 10680, "error": 4}
EXPECTED_MAGNETISM_STATUS = {"ok": 10684}


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

    if report.output_rows != EXPECTED_ROWS or len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} rows, got report={report.output_rows}, csv={len(rows)}")

    require_counter(rows, "analysis_cohort", EXPECTED_COHORTS)
    require_counter(rows, "descriptor_v1_status", EXPECTED_DESCRIPTOR_STATUS)
    require_counter(rows, "energy_status", EXPECTED_ENERGY_STATUS)
    require_counter(rows, "magnetism_status", EXPECTED_MAGNETISM_STATUS)

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
