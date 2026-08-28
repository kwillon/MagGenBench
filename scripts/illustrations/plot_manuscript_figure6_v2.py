from __future__ import annotations

from mvpipeline.analysis.manuscript_figure6_v2 import (
    run_manuscript_figure6,
)


def main() -> int:
    report = run_manuscript_figure6()

    print("===== Manuscript Figure 6 =====")
    print(
        f"input: {report.input_csv}"
    )
    print(
        f"rows: {report.n_rows}"
    )

    print("\n===== Compound classes =====")
    for index, label in enumerate(
        report.class_order,
        start=1,
    ):
        print(
            f"{index:2d}. {label}"
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
        "MANUSCRIPT_FIGURE6_V2: PASSED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
