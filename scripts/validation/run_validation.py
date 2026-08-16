#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "src"))

from mvpipeline.validation.run_config import (  # noqa: E402
    VALIDATION_COHORTS,
    get_validation_cohort,
    run_validation_command,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a configured MagGenBench validation cohort."
    )
    parser.add_argument(
        "--cohort",
        required=True,
        choices=tuple(VALIDATION_COHORTS),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--mvp",
        default="mvp",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_validation_command(
            get_validation_cohort(args.cohort),
            repo_root=args.repo_root,
            mvp_executable=args.mvp,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

