#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "src"))

from mvpipeline.annotations.production_manifest import (  # noqa: E402
    run_production_manifest,
)


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Build the Phase 5A-6 production enrichment cohort "
            "from validated, loadable structures."
        )
    )
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


def main():
    args = parse_args()
    run_production_manifest(
        input_path=Path(args.input),
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()

