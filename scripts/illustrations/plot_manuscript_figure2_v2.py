from __future__ import annotations

from mvpipeline.analysis.manuscript_figure2_v2 import (
    run_manuscript_figure2,
)


def main() -> int:
    report = run_manuscript_figure2()

    print("===== Manuscript Figure 2 =====")
    print(
        f"analysis_input: "
        f"{report.analysis_input_csv}"
    )
    print(
        f"validation_input: "
        f"{report.validation_input_csv}"
    )

    print("\n===== Analysis v2 cohort sizes =====")
    print(
        report.analysis_counts.to_string()
    )

    print("\n===== Baseline validation =====")
    print(
        report.validation_summary
        .round(3)
        .to_string()
    )

    print("\n===== Figure =====")
    print(
        f"figure_png: "
        f"{report.figure_paths.png}"
    )
    print(
        f"figure_pdf: "
        f"{report.figure_paths.pdf}"
    )
    print(
        f"figure_svg: "
        f"{report.figure_paths.svg}"
    )

    print(
        "MANUSCRIPT_FIGURE2_V2: PASSED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
