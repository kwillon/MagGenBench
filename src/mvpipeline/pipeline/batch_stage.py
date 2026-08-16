from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from ..io.stage_tables import (
    merge_stage_records_incremental,
    read_stage_csv,
    write_stage_csv_atomic,
)
from .stage_common import PreparedStructureRecord, success_ids_from_records


class ChunkRunner(Protocol):
    def __call__(
        self,
        records: Sequence[PreparedStructureRecord],
    ) -> Iterable[Mapping[str, Any]]:
        """Run one checkpoint chunk and return stage-result records."""


SuccessIds = Callable[[Iterable[Mapping[str, Any]]], frozenset[str]]


@dataclass(frozen=True)
class CheckpointedBatchReport:
    output_path: Path
    previous_results: list[Mapping[str, Any]]
    resume_success_ids: frozenset[str]
    pending_records: list[PreparedStructureRecord]
    records: list[Mapping[str, Any]]
    new_result_count: int
    checkpoint_count: int


def run_checkpointed_batch(
    *,
    prepared_records: Sequence[PreparedStructureRecord],
    output_path: str | Path,
    fieldnames: Sequence[str],
    checkpoint_every: int,
    previous_results: Iterable[Mapping[str, Any]],
    run_chunk: ChunkRunner,
    success_ids_from_previous: SuccessIds = success_ids_from_records,
) -> CheckpointedBatchReport:
    """Run a resumable stage batch while preserving manifest order.

    This owns only the mechanical checkpoint/resume loop shared by the
    production CHGNet and DXMag batch wrappers. Backend construction,
    prepared-record construction, stage semantics, and status summaries stay
    with the caller.
    """
    if checkpoint_every <= 0:
        raise ValueError("--checkpoint-every must be > 0")

    output = Path(output_path)
    previous = list(previous_results)

    resume_success_ids = success_ids_from_previous(previous)

    structure_ids = [
        record.structure_id
        for record in prepared_records
    ]

    checkpoint_records = merge_stage_records_incremental(
        structure_ids=structure_ids,
        previous_records=previous,
        new_records=[],
    )

    pending = [
        record
        for record in prepared_records
        if record.structure_id not in resume_success_ids
    ]
    new_result_count = 0
    checkpoint_count = 0

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    for start in range(
        0,
        len(pending),
        checkpoint_every,
    ):
        chunk = pending[
            start : start + checkpoint_every
        ]
        chunk_results = list(run_chunk(chunk))
        new_result_count += len(chunk_results)
        checkpoint_count += 1

        checkpoint_records = merge_stage_records_incremental(
            structure_ids=structure_ids,
            previous_records=checkpoint_records,
            new_records=chunk_results,
        )

        write_stage_csv_atomic(
            output,
            checkpoint_records,
            fieldnames,
        )

        print(
            "checkpoint:",
            checkpoint_count,
            "processed:",
            new_result_count,
            "saved_rows:",
            len(checkpoint_records),
        )

    if not pending:
        write_stage_csv_atomic(
            output,
            checkpoint_records,
            fieldnames,
        )

    results = list(checkpoint_records)

    if len(results) != len(prepared_records):
        raise RuntimeError(
            f"Expected {len(prepared_records)} final results, "
            f"got {len(results)}"
        )

    if [
        row["structure_id"] for row in results
    ] != structure_ids:
        raise RuntimeError(
            "Final result order does not match manifest order"
        )

    return CheckpointedBatchReport(
        output_path=output,
        previous_results=previous,
        resume_success_ids=resume_success_ids,
        pending_records=pending,
        records=results,
        new_result_count=new_result_count,
        checkpoint_count=checkpoint_count,
    )


def load_previous_stage_results(
    *,
    resume: bool,
    output_path: str | Path,
) -> list[dict[str, str]]:
    if resume and Path(output_path).exists():
        return read_stage_csv(output_path)
    return []
