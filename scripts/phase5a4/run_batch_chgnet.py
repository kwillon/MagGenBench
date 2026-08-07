from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from batch_common import (
    load_manifest_rows,
    prepare_records,
    status_summary,
)

from mvpipeline.energy.backends.chgnet import CHGNetBackend
from mvpipeline.energy.records import ENERGY_RECORD_FIELDS
from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.pipeline.energy_stage import run_energy_stage


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
    p.add_argument(
        "--device",
        default=None,
        help="Optional CHGNet device override, e.g. cpu or cuda.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    rows = load_manifest_rows(args.manifest)
    prepared = prepare_records(
        rows,
        source="phase5a4_batch_chgnet",
    )

    with Path("config/energy.yaml").open(
        encoding="utf-8",
    ) as handle:
        settings = yaml.safe_load(handle)["energy"]["chgnet"]

    device = args.device or settings["device"]

    backend = CHGNetBackend(
        model_name=settings["model_name"],
        model_selector=settings["model_selector"],
        device=device,
        output_semantics=settings["output_semantics"],
    )

    print("===== Phase 5A-4 CHGNet batch =====")
    print("input_count:", len(prepared))
    print("configured_device:", settings["device"])
    print("runtime_device:", device)

    report = run_energy_stage(
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
        ENERGY_RECORD_FIELDS,
    )

    ok, error = status_summary(results)

    print("output:", args.output.resolve())
    print("row_count:", len(results))
    print("ok:", ok)
    print("error:", error)
    print("plan:", report.plan)

    print("\nPHASE5A4_CHGNET_BATCH: PASSED")


if __name__ == "__main__":
    main()
