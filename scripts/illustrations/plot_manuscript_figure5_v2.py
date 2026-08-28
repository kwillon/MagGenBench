from __future__ import annotations

from mvpipeline.analysis.manuscript_figure5_v2 import (
    run_manuscript_figure5,
)


def main() -> int:
    report = run_manuscript_figure5()

    print("===== Manuscript Figure 5 =====")
    print(f"input: {report.input_csv}")

    print("\n===== Energy–magnetism population =====")
    print(
        "analysis rows:",
        report.n_total,
    )
    print(
        "paired energy/moment rows:",
        report.n_paired,
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
        "MANUSCRIPT_FIGURE5_V2: PASSED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
