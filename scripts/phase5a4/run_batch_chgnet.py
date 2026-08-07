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
from mvpipeline.io.stage_tables import (
    merge_stage_records_incremental,
    read_stage_csv,
    write_stage_csv_atomic,
)
from mvpipeline.pipeline.energy_stage import run_energy_stage
from mvpipeline.pipeline.stage_common import success_ids_from_records


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

    previous_results = []
    if args.resume and args.output.exists():
        previous_results = read_stage_csv(args.output)

    resume_success_ids = success_ids_from_records(
        previous_results
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

    if args.checkpoint_every <= 0:
        raise ValueError("--checkpoint-every must be > 0")

    structure_ids = [
        record.structure_id for record in prepared
    ]

    checkpoint_records = (
        merge_stage_records_incremental(
            structure_ids=structure_ids,
            previous_records=previous_results,
            new_records=[],
        )
    )

    pending = [
        record
        for record in prepared
        if record.structure_id not in resume_success_ids
    ]
    new_result_count = 0
    chunk_count = 0

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    for start in range(
        0,
        len(pending),
        args.checkpoint_every,
    ):
        chunk = pending[
            start : start + args.checkpoint_every
        ]

        report = run_energy_stage(
            chunk,
            backend=backend,
            fail_fast=False,
        )

        chunk_results = list(report.records)
        new_result_count += len(chunk_results)
        chunk_count += 1

        checkpoint_records = (
            merge_stage_records_incremental(
                structure_ids=structure_ids,
                previous_records=checkpoint_records,
                new_records=chunk_results,
            )
        )

        write_stage_csv_atomic(
            args.output,
            checkpoint_records,
            ENERGY_RECORD_FIELDS,
        )

        print(
            "checkpoint:",
            chunk_count,
            "processed:",
            new_result_count,
            "saved_rows:",
            len(checkpoint_records),
        )

    if not pending:
        write_stage_csv_atomic(
            args.output,
            checkpoint_records,
            ENERGY_RECORD_FIELDS,
        )

    results = list(checkpoint_records)

    if len(results) != len(prepared):
        raise RuntimeError(
            f"Expected {len(prepared)} final results, "
            f"got {len(results)}"
        )

    if [
        row["structure_id"] for row in results
    ] != structure_ids:
        raise RuntimeError(
            "Final result order does not match manifest order"
        )

    ok, error = status_summary(results)

    print("output:", args.output.resolve())
    print(
        "resumed_success_count:",
        len(resume_success_ids),
    )
    print("pending_count:", len(pending))
    print("new_result_count:", new_result_count)
    print("checkpoint_count:", chunk_count)
    print("row_count:", len(results))
    print("ok:", ok)
    print("error:", error)

    print("\nPHASE5A4_CHGNET_BATCH: PASSED")


if __name__ == "__main__":
    main()
