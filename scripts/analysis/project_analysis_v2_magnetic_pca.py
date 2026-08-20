from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from mvpipeline.analysis.plotting_v2 import ANALYSIS_V2_FIGURE_OUTPUT_DIR
from mvpipeline.analysis.projections_v2 import (
    PCA_OUTPUT_DIR,
    generate_analysis_v2_pca_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Analysis v2 magnetic descriptor-space PCA outputs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ANALYSIS_V2_MAGNETIC_INPUT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PCA_OUTPUT_DIR,
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=ANALYSIS_V2_FIGURE_OUTPUT_DIR,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = generate_analysis_v2_pca_outputs(
        input_csv=args.input,
        output_dir=args.output_dir,
        figure_dir=args.figure_dir,
    )
    print("===== Analysis v2 magnetic PCA =====")
    print("input:", report.input_csv)
    print("composition_scores:", report.composition_scores_csv)
    print("composition_loadings:", report.composition_loadings_csv)
    print("magnetic_geometry_scores:", report.magnetic_geometry_scores_csv)
    print("magnetic_geometry_loadings:", report.magnetic_geometry_loadings_csv)
    print("summary:", report.summary_markdown)
    for paths in report.figure_paths:
        print("figure_png:", paths.png)
        print("figure_pdf:", paths.pdf)
        print("figure_svg:", paths.svg)
    print("ANALYSIS_V2_MAGNETIC_PCA: PASSED")


if __name__ == "__main__":
    main()
