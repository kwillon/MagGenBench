from __future__ import annotations

from mvpipeline.analysis.workflow_figure_v2 import (
    run_study_workflow,
)


def main() -> int:
    report = run_study_workflow()

    print("===== Study workflow =====")
    print(f"figure_png: {report.figure_paths.png}")
    print(f"figure_pdf: {report.figure_paths.pdf}")
    print(f"figure_svg: {report.figure_paths.svg}")
    print("ANALYSIS_V2_WORKFLOW: PASSED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
