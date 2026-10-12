from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.figures_v2_magnetic import ANALYSIS_V2_MAGNETIC_INPUT
from mvpipeline.analysis.manuscript_figure3_v2 import COHORT_ORDER, run_manuscript_figure3
from mvpipeline.analysis.plotting_v2 import ANALYSIS_V2_FIGURE_OUTPUT_DIR
from mvpipeline.descriptors.figure3_ft import STANDARDIZED_INPUT


def cohort_paths(values, parser):
    result = {}
    for value in values:
        key, separator, path = value.partition("=")
        if not separator or key not in COHORT_ORDER or not path or key in result:
            parser.error("Expected a unique COHORT=PATH with a known cohort name")
        result[key] = Path(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Figure 3: magnetic-domain descriptors for ten QC sets")
    parser.add_argument("--input", type=Path, default=ANALYSIS_V2_MAGNETIC_INPUT)
    parser.add_argument("--qc-input", action="append", default=[], metavar="COHORT=PATH")
    parser.add_argument("--descriptor-input", action="append", default=[], metavar="COHORT=PATH")
    parser.add_argument("--figure-dir", type=Path, default=ANALYSIS_V2_FIGURE_OUTPUT_DIR)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--standardized-input", type=Path, default=STANDARDIZED_INPUT)
    parser.add_argument("--require-complete-descriptors", action="store_true")
    args = parser.parse_args()
    report = run_manuscript_figure3(
        args.input, args.figure_dir, audit_only=args.audit_only,
        qc_inputs=cohort_paths(args.qc_input, parser),
        descriptor_inputs=cohort_paths(args.descriptor_input, parser),
        standardized_input=args.standardized_input,
        require_complete_descriptors=args.require_complete_descriptors,
    )
    print(report.audit.to_string())
    if report.missing_inputs:
        print("\nMissing sources (no complete scientific export):")
        for path in report.missing_inputs:
            print(path)
        return 2
    if report.figure_paths:
        for fmt in ("png", "pdf", "svg"):
            print(f"figure_{fmt}: {getattr(report.figure_paths, fmt)}")
    print("MANUSCRIPT_FIGURE3_V2: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
