from __future__ import annotations

from mvpipeline.analysis.compound_classes_v2 import (
    run_analysis_v2_compound_classes,
)


def main() -> int:
    report = run_analysis_v2_compound_classes()

    print("===== Compound-class analysis figures =====")
    print(f"input: {report.input_csv}")
    print(f"class order: {', '.join(report.class_order)}")

    print("\n===== Distribution, % within generated set =====")
    print(report.distribution_table.round(2).to_string())

    print("\n===== Adaptation deltas, percentage points =====")
    print(report.adaptation_delta_table.round(2).to_string())

    print("\n===== Tables =====")
    print(f"distribution_csv: {report.distribution_csv}")
    print(f"adaptation_delta_csv: {report.adaptation_delta_csv}")

    print("\n===== Figures =====")
    for paths in report.figure_paths:
        print(f"figure_png: {paths.png}")
        print(f"figure_pdf: {paths.pdf}")
        print(f"figure_svg: {paths.svg}")

    print("ANALYSIS_V2_COMPOUND_CLASSES: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
