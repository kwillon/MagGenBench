#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "src"))

from mvpipeline.annotations.finetuned import (  # noqa: E402
    FINETUNED_COHORTS,
    get_finetuned_cohort,
    run_finetuned_annotation_preparation,
)


def parse_args():
    p = argparse.ArgumentParser(
        description="Prepare active fine-tuned annotation manifests."
    )
    p.add_argument(
        "--cohort",
        required=True,
        choices=tuple(FINETUNED_COHORTS),
    )
    p.add_argument(
        "--repo-root",
        default=str(ROOT),
    )
    return p.parse_args()


def main():
    args = parse_args()
    run_finetuned_annotation_preparation(
        cohort=get_finetuned_cohort(args.cohort),
        repo_root=Path(args.repo_root),
    )


if __name__ == "__main__":
    main()

