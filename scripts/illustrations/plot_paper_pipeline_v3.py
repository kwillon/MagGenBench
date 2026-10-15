from __future__ import annotations

from mvpipeline.analysis.paper_pipeline_figure_v3 import (
    run_paper_pipeline_figure_v3,
)


def main() -> int:
    report = run_paper_pipeline_figure_v3()

    print("===== Manuscript-style analysis pipeline v3 =====")
    print(f"figure_png: {report.figure_paths.png}")
    print(f"figure_pdf: {report.figure_paths.pdf}")
    print(f"figure_svg: {report.figure_paths.svg}")
    print("ANALYSIS_V2_PAPER_PIPELINE_V3: PASSED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
