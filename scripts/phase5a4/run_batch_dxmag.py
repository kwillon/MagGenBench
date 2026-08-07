from __future__ import annotations

import argparse
from pathlib import Path

from batch_common import (
    load_manifest_rows,
    prepare_records,
    status_summary,
)

from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.magnetism.backends.sklearn import (
    SklearnMagnetismBackend,
)
from mvpipeline.magnetism.config import load_magnetism_config
from mvpipeline.magnetism.records import MAGNETISM_RECORD_FIELDS
from mvpipeline.pipeline.magnetism_stage import (
    run_magnetism_stage,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    rows = load_manifest_rows(args.manifest)
    prepared = prepare_records(
        rows,
        source="phase5a4_batch_dxmag",
    )

    config = load_magnetism_config(
        "config/magnetism.yaml"
    )

    backend = SklearnMagnetismBackend(
        settings=config.sklearn,
    )

    print("===== Phase 5A-4 DXMag batch =====")
    print("input_count:", len(prepared))

    report = run_magnetism_stage(
        prepared,
        backend=backend,
        fail_fast=False,
    )

    results = list(report.records)

    if len(results) != len(prepared):
        raise RuntimeError(
            f"Expected {len(prepared)} results, "
            f"got {len(results)}"
        )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_stage_csv_atomic(
        args.output,
        results,
        MAGNETISM_RECORD_FIELDS,
    )

    ok, error = status_summary(results)

    print("output:", args.output.resolve())
    print("row_count:", len(results))
    print("ok:", ok)
    print("error:", error)
    print("plan:", report.plan)

    print("\nPHASE5A4_DXMAG_BATCH: PASSED")


if __name__ == "__main__":
    main()
