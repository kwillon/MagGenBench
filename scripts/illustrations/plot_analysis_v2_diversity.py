from __future__ import annotations

from mvpipeline.analysis.diversity_figures_v2 import (
    run_analysis_v2_diversity,
)


def main() -> int:
    report = run_analysis_v2_diversity()

    print("===== Chemical uniqueness analysis =====")
    print(f"input: {report.input_csv}")

    print("\n===== Generated-set summary =====")
    print(report.summary_table.round(3).to_string())

    print("\n===== Adaptation/refinement deltas, percentage points =====")
    print(report.adaptation_delta_table.round(3).to_string())

    print("\n===== Audit tables =====")
    print(f"summary_csv: {report.summary_csv}")
    print(f"adaptation_delta_csv: {report.adaptation_delta_csv}")

    print("\n===== Figure =====")
    print(f"figure_png: {report.figure_paths.png}")
    print(f"figure_pdf: {report.figure_paths.pdf}")
    print(f"figure_svg: {report.figure_paths.svg}")

    print("ANALYSIS_V2_DIVERSITY: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
