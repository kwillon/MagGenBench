from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.figures_v2_magnetic import (
    ANALYSIS_V2_AUDIT_OUTPUT_DIR,
    ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    ANALYSIS_V2_MAGNETIC_INPUT,
    audit_analysis_v2_magnetic_inputs,
    generate_analysis_v2_magnetic_preview_figure,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate first publication-style Analysis v2 magnetic preview."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ANALYSIS_V2_MAGNETIC_INPUT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = audit_analysis_v2_magnetic_inputs(
        input_csv=args.input,
        output_dir=ANALYSIS_V2_AUDIT_OUTPUT_DIR
        if args.output_dir == ANALYSIS_V2_FIGURE_OUTPUT_DIR
        else args.output_dir.parent / "audit",
    )
    preview = generate_analysis_v2_magnetic_preview_figure(
        input_csv=args.input,
        output_dir=args.output_dir,
    )

    print("===== Analysis v2 magnetic preview figure =====")
    print("input:", preview.input_csv)
    print("audit_csv:", audit.audit_csv)
    print("audit_markdown:", audit.audit_markdown)
    print("png:", preview.figure_paths.png)
    print("pdf:", preview.figure_paths.pdf)
    print("svg:", preview.figure_paths.svg)
    print("ANALYSIS_V2_MAGNETIC_PREVIEW_FIGURE: PASSED")


if __name__ == "__main__":
    main()
