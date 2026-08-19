from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.analysis.magnetic_v2 import (
    DEFAULT_ANALYSIS_V2_MAGNETIC_OUTPUT_PATH,
    DESCRIPTOR_V2_MAGNETIC_PATH,
    STANDARDIZED_ENRICHMENT_PATH,
    build_analysis_v2_magnetic,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build generated Analysis v2 magnetic dataset."
    )
    parser.add_argument(
        "--standardized-enrichment",
        type=Path,
        default=STANDARDIZED_ENRICHMENT_PATH,
    )
    parser.add_argument(
        "--descriptor-v2",
        type=Path,
        default=DESCRIPTOR_V2_MAGNETIC_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ANALYSIS_V2_MAGNETIC_OUTPUT_PATH,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report = build_analysis_v2_magnetic(
        standardized_enrichment_path=args.standardized_enrichment,
        descriptor_v2_path=args.descriptor_v2,
        output_path=args.output,
    )

    print("===== Analysis v2 magnetic =====")
    print("standardized_enrichment:", args.standardized_enrichment)
    print("descriptor_v2:", args.descriptor_v2)
    print("output:", report.output_path)
    print("standardized_rows:", report.standardized_rows)
    print("descriptor_v2_rows:", report.descriptor_v2_rows)
    print("output_rows:", report.output_rows)
    print("standardized_columns:", report.standardized_columns)
    print("descriptor_v2_columns:", report.descriptor_v2_columns)
    print("output_columns:", report.output_columns)
    print("ANALYSIS_V2_MAGNETIC: PASSED")


if __name__ == "__main__":
    main()
