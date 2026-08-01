from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Optional

from ..magnetism import MagnetismInput
from ..magnetism.backends.base import MagnetismBackend
from ..magnetism.backends.factory import create_magnetism_backend
from ..magnetism.records import magnetic_result_to_record
from .stage_common import (
    InputPreparer,
    PreparedStructureRecord,
    StageRunReport,
    StageRunSettings,
    run_stage_records,
)


def prepare_magnetism_input(record: PreparedStructureRecord) -> MagnetismInput:
    return MagnetismInput(
        structure_id=record.structure_id,
        structure=record.structure,
        composition=record.composition,
        features=record.features,
    )


def run_magnetism_stage(
    records: Iterable[Mapping[str, Any] | PreparedStructureRecord],
    *,
    backend: Optional[MagnetismBackend] = None,
    backend_selector: str | Mapping[str, object] = "fake",
    preparer: InputPreparer = prepare_magnetism_input,
    limit: Optional[int] = None,
    dry_run: bool = False,
    fail_fast: bool = False,
    resume_success_ids: Optional[set[str] | frozenset[str]] = None,
    resume_success_predicate: Optional[Callable[[str], bool]] = None,
) -> StageRunReport:
    selected_backend = (
        backend if backend is not None else create_magnetism_backend(backend_selector)
    )
    settings = StageRunSettings(
        stage_name="magnetism",
        backend_selector=(
            backend_selector if isinstance(backend_selector, str) else "configured"
        ),
        limit=limit,
        dry_run=dry_run,
        fail_fast=fail_fast,
        resume_success_ids=frozenset(resume_success_ids or ()),
        resume_success_predicate=resume_success_predicate,
    )
    return run_stage_records(
        records=records,
        settings=settings,
        backend=selected_backend,
        preparer=preparer,
        result_to_record=magnetic_result_to_record,
    )
