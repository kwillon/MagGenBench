from __future__ import annotations

from mvpipeline.analysis.manuscript_figure4_v2 import (
    run_manuscript_figure4,
)


def main() -> int:
    report = run_manuscript_figure4()

    print("===== Manuscript Figure 4 =====")
    print(f"input: {report.input_csv}")

    print("\n===== PCA populations =====")
    print(
        "composition/symmetry rows:",
        report.n_composition_rows,
    )
    print(
        "magnetic-geometry rows:",
        report.n_magnetic_geometry_rows,
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

    print("MANUSCRIPT_FIGURE4_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
