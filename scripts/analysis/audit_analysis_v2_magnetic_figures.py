from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.figures_v2_magnetic import (
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_INPUT,
    audit_analysis_v2_magnetic_inputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Analysis v2 magnetic inputs for figure design."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ANALYSIS_V2_MAGNETIC_INPUT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_analysis_v2_magnetic_inputs(
        input_csv=args.input,
        output_dir=args.output_dir,
    )
    print("===== Analysis v2 magnetic figure-input audit =====")
    print("input:", report.input_csv)
    print("audit_csv:", report.audit_csv)
    print("audit_markdown:", report.audit_markdown)
    print("energy_columns:", ", ".join(report.energy_columns))
    print("dxmag_columns:", ", ".join(report.dxmag_columns))
    print("ANALYSIS_V2_MAGNETIC_FIGURE_AUDIT: PASSED")


if __name__ == "__main__":
    main()
