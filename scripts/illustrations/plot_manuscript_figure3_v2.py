from __future__ import annotations

from mvpipeline.analysis.manuscript_figure3_v2 import (
    run_manuscript_figure3,
)


def main() -> int:
    report = run_manuscript_figure3()

    print("===== Manuscript Figure 3 =====")
    print(f"input: {report.input_csv}")

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

    print("MANUSCRIPT_FIGURE3_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
