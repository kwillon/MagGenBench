from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.manuscript_figure2_v2 import QC_INPUTS, run_manuscript_figure2
from mvpipeline.analysis.plotting_v2 import ANALYSIS_V2_FIGURE_OUTPUT_DIR
from mvpipeline.analysis.validation_figures_v2 import VALIDATION_INPUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Figure 2: ten structural QC benchmark cohorts")
    parser.add_argument("--validation-input", type=Path, default=VALIDATION_INPUT)
    parser.add_argument("--figure-dir", type=Path, default=ANALYSIS_V2_FIGURE_OUTPUT_DIR)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--check-expected", action="store_true")
    for cohort, path in QC_INPUTS.items():
        parser.add_argument("--" + cohort.replace("_", "-"), type=Path, default=path)
    args = parser.parse_args()
    report = run_manuscript_figure2(
        validation_input_csv=args.validation_input, figure_dir=args.figure_dir,
        qc_inputs={key: getattr(args, key) for key in QC_INPUTS},
        audit_only=args.audit_only, check_expected=args.check_expected,
    )
    print("Structural QC counts (not CHGNet, DXMag or descriptor success counts):")
    print(report.qc_summary.to_string())
    print(f"Verified available retained total: {int(report.qc_summary['n_validated'].sum())}")
    if report.missing_inputs:
        print("Missing QC tables:")
        for path in report.missing_inputs:
            print(path)
        return 2
    if report.figure_paths:
        for fmt in ("png", "pdf", "svg"):
            print(f"figure_{fmt}: {getattr(report.figure_paths, fmt)}")
    print("MANUSCRIPT_FIGURE2_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
