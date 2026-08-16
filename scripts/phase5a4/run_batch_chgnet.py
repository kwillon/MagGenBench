from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from batch_common import (
    prepare_records,
    status_summary,
)

from mvpipeline.energy.backends.chgnet import CHGNetBackend
from mvpipeline.energy.records import ENERGY_RECORD_FIELDS
from mvpipeline.io.manifests import load_manifest_rows
from mvpipeline.pipeline.batch_stage import (
    load_previous_stage_results,
    run_checkpointed_batch,
)
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
    p.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse successful rows already present in --output "
            "and rerun only missing or failed structure IDs."
        ),
    )
    p.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help=(
            "Atomically update the output CSV after this many "
            "newly processed structures."
        ),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    rows = load_manifest_rows(args.manifest)
    previous_results = load_previous_stage_results(
        resume=args.resume,
        output_path=args.output,
    )

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

    def run_chunk(chunk):
        report = run_energy_stage(
            chunk,
            backend=backend,
            fail_fast=False,
        )
        return list(report.records)

    batch_report = run_checkpointed_batch(
        prepared_records=prepared,
        output_path=args.output,
        fieldnames=ENERGY_RECORD_FIELDS,
        checkpoint_every=args.checkpoint_every,
        previous_results=previous_results,
        run_chunk=run_chunk,
    )

    ok, error = status_summary(batch_report.records)

    print("output:", args.output.resolve())
    print(
        "resumed_success_count:",
        len(batch_report.resume_success_ids),
    )
    print("pending_count:", len(batch_report.pending_records))
    print("new_result_count:", batch_report.new_result_count)
    print("checkpoint_count:", batch_report.checkpoint_count)
    print("row_count:", len(batch_report.records))
    print("ok:", ok)
    print("error:", error)

    print("\nPHASE5A4_CHGNET_BATCH: PASSED")


if __name__ == "__main__":
    main()
