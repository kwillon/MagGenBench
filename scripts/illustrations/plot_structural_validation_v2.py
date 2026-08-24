from __future__ import annotations

from mvpipeline.analysis.validation_figures_v2 import (
    run_structural_validation_figure,
)


def main() -> int:
    report = run_structural_validation_figure()

    print("===== Structural validation figure =====")
    print(f"input: {report.input_csv}")
    print(f"rows: {report.n_rows}")

    print("\n===== Validation summary =====")
    print(report.model_summary.round(2).to_string())

    print("\n===== Rejection profile, % within rejected =====")
    print(report.rejection_summary.round(2).to_string())

    print("\n===== Audit tables =====")
    print(f"model_summary_csv: {report.model_summary_csv}")
    print(f"rejection_summary_csv: {report.rejection_summary_csv}")

    print("\n===== Figure =====")
    print(f"figure_png: {report.figure_paths.png}")
    print(f"figure_pdf: {report.figure_paths.pdf}")
    print(f"figure_svg: {report.figure_paths.svg}")

    print("STRUCTURAL_VALIDATION_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
