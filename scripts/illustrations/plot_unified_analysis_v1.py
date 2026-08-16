from __future__ import annotations

from mvpipeline.analysis.figures_v1 import generate_crystal_system_figures
from mvpipeline.analysis.plotting import (
    repository_root_from_script,
    unified_analysis_figure_dir,
    unified_analysis_v1_path,
)


def main() -> None:
    root = repository_root_from_script(__file__)
    input_path = unified_analysis_v1_path(root)
    output_dir = unified_analysis_figure_dir(root)

    outputs = generate_crystal_system_figures(input_path, output_dir)

    print("INPUT:", input_path)
    print("OUTPUT_DIR:", output_dir)
    print("FILES:")
    for path in outputs:
        print(" ", path)
    print("PLOT_UNIFIED_ANALYSIS_V1: PASSED")


if __name__ == "__main__":
    main()
