from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol, Sequence


SUCCESS_STATUS = "ok"


class ResultRecordConverter(Protocol):
    def __call__(self, result: Any) -> dict[str, Any]:
        """Convert a typed stage result to a flat record."""


class InputPreparer(Protocol):
    def __call__(self, record: "PreparedStructureRecord") -> Any:
        """Build a typed stage input from a prepared structure record."""


ResumePredicate = Callable[[str], bool]


@dataclass(frozen=True)
class PreparedStructureRecord:
    structure_id: str
    order: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    structure: Any = None
    n_atoms: Optional[int] = None
    composition: Mapping[str, float] = field(default_factory=dict)
    features: Optional[Sequence[float]] = None

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any], order: int
    ) -> "PreparedStructureRecord":
        structure_id = data.get("structure_id")
        if not structure_id:
            raise ValueError("Prepared record is missing required structure_id")
        known = {"structure_id", "structure", "n_atoms", "composition", "features"}
        metadata = {key: value for key, value in data.items() if key not in known}
        n_atoms = data.get("n_atoms")
        return cls(
            structure_id=str(structure_id),
            order=order,
            metadata=metadata,
            structure=data.get("structure"),
            n_atoms=None if n_atoms is None else int(n_atoms),
            composition=data.get("composition", {}) or {},
            features=data.get("features"),
        )


@dataclass(frozen=True)
class StageRunSettings:
    stage_name: str
    backend_selector: str = "fake"
    limit: Optional[int] = None
    dry_run: bool = False
    fail_fast: bool = False
    resume_success_ids: frozenset[str] = frozenset()
    resume_success_predicate: Optional[ResumePredicate] = None

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise ValueError("limit must be None or non-negative")


@dataclass(frozen=True)
class StagePlan:
    stage_name: str
    backend_name: str
    input_count: int
    skipped_count: int
    planned_count: int
    limit: Optional[int]
    dry_run: bool
    fail_fast: bool


@dataclass(frozen=True)
class StageRunReport:
    plan: StagePlan
    records: list[dict[str, Any]]


def materialize_prepared_records(
    records: Iterable[Mapping[str, Any] | PreparedStructureRecord],
) -> list[PreparedStructureRecord]:
    prepared: list[PreparedStructureRecord] = []
    seen: set[str] = set()
    for order, record in enumerate(records):
        item = (
            record
            if isinstance(record, PreparedStructureRecord)
            else PreparedStructureRecord.from_mapping(record, order)
        )
        if item.structure_id in seen:
            raise ValueError(
                f"Duplicate structure_id in stage input: {item.structure_id}"
            )
        seen.add(item.structure_id)
        prepared.append(item)
    return prepared


def should_skip_for_resume(
    structure_id: str,
    success_ids: set[str],
    success_predicate: Optional[ResumePredicate],
) -> bool:
    if structure_id in success_ids:
        return True
    if success_predicate is not None:
        return bool(success_predicate(structure_id))
    return False


def success_ids_from_records(records: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    return frozenset(
        str(record["structure_id"])
        for record in records
        if record.get("structure_id") and record.get("status") == SUCCESS_STATUS
    )


def select_records_for_run(
    records: Sequence[PreparedStructureRecord],
    settings: StageRunSettings,
) -> tuple[list[PreparedStructureRecord], int]:
    success_ids = set(settings.resume_success_ids)
    filtered = [
        record
        for record in records
        if not should_skip_for_resume(
            record.structure_id, success_ids, settings.resume_success_predicate
        )
    ]
    if settings.limit is None:
        return filtered, len(records) - len(filtered)
    return filtered[: settings.limit], len(records) - len(filtered)


def get_backend_name(backend: Any, fallback: str) -> str:
    return str(getattr(backend, "name", fallback))


def base_stage_record(
    *,
    stage_name: str,
    backend_name: str,
    item: PreparedStructureRecord,
) -> dict[str, Any]:
    record = {
        "structure_id": item.structure_id,
        "input_order": item.order,
        "stage_name": stage_name,
        "backend": backend_name,
    }
    record.update(item.metadata)
    return record


def failure_record(
    *,
    stage_name: str,
    backend_name: str,
    item: PreparedStructureRecord,
    error_code: str,
    error_message: str,
) -> dict[str, Any]:
    record = base_stage_record(
        stage_name=stage_name,
        backend_name=backend_name,
        item=item,
    )
    record.update(
        {
            "status": "error",
            "error_code": error_code,
            "error_message": error_message,
        }
    )
    return record


def merge_stage_result_record(
    *,
    stage_name: str,
    backend_name: str,
    item: PreparedStructureRecord,
    result_record: Mapping[str, Any],
) -> dict[str, Any]:
    merged = base_stage_record(
        stage_name=stage_name,
        backend_name=backend_name,
        item=item,
    )
    merged.update(result_record)
    merged["input_order"] = item.order
    merged["stage_name"] = stage_name
    if not merged.get("backend"):
        merged["backend"] = backend_name
    return merged


def run_stage_records(
    *,
    records: Iterable[Mapping[str, Any] | PreparedStructureRecord],
    settings: StageRunSettings,
    backend: Any,
    preparer: InputPreparer,
    result_to_record: ResultRecordConverter,
) -> StageRunReport:
    prepared = materialize_prepared_records(records)
    selected, skipped_count = select_records_for_run(prepared, settings)
    backend_name = get_backend_name(backend, settings.backend_selector)
    plan = StagePlan(
        stage_name=settings.stage_name,
        backend_name=backend_name,
        input_count=len(prepared),
        skipped_count=skipped_count,
        planned_count=len(selected),
        limit=settings.limit,
        dry_run=settings.dry_run,
        fail_fast=settings.fail_fast,
    )
    if settings.dry_run:
        return StageRunReport(plan=plan, records=[])

    output: list[dict[str, Any]] = []
    for item in selected:
        try:
            stage_input = preparer(item)
            result = backend.predict(stage_input)
            output.append(
                merge_stage_result_record(
                    stage_name=settings.stage_name,
                    backend_name=backend_name,
                    item=item,
                    result_record=result_to_record(result),
                )
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            if settings.fail_fast:
                raise
            output.append(
                failure_record(
                    stage_name=settings.stage_name,
                    backend_name=backend_name,
                    item=item,
                    error_code="stage_record_error",
                    error_message=str(exc),
                )
            )
    return StageRunReport(plan=plan, records=output)
