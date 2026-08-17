from __future__ import annotations

import argparse
from pathlib import Path

from mvpipeline.descriptors.batch_v2 import run_magnetic_descriptor_v2_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Magnetic Descriptor v2 over a standardized input CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "tables/08_standardized_enrichment/standardized_enrichment.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reproduced/descriptor_v2_magnetic/descriptor_v2_magnetic.csv"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/descriptors_v2_magnetic.yaml"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional small row limit for smoke tests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report = run_magnetic_descriptor_v2_batch(
        input_path=args.input,
        output_path=args.output,
        descriptor_config_path=args.config,
        project_root=args.repo_root,
        limit=args.limit,
    )

    print("===== Magnetic Descriptor v2 batch =====")
    print("input:", args.input)
    print("output:", report.output_path)
    print("input_count:", report.input_count)
    print("output_count:", report.output_count)
    print("columns:", len(report.fieldnames))
    print("\nDESCRIPTOR_V2_MAGNETIC: PASSED")


if __name__ == "__main__":
    main()
