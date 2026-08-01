from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional

from ..energy.backends.base import EnergyBackend
from ..magnetism.backends.base import MagnetismBackend
from .energy_stage import run_energy_stage
from .magnetism_stage import run_magnetism_stage
from .stage_common import PreparedStructureRecord, StageRunReport


@dataclass(frozen=True)
class EnrichmentReport:
    energy: Optional[StageRunReport] = None
    magnetism: Optional[StageRunReport] = None


def run_enrichment(
    records: Iterable[Mapping[str, Any] | PreparedStructureRecord],
    *,
    run_energy: bool = True,
    run_magnetism: bool = True,
    energy_backend: Optional[EnergyBackend] = None,
    magnetism_backend: Optional[MagnetismBackend] = None,
    energy_backend_selector: str | Mapping[str, object] = "fake",
    magnetism_backend_selector: str | Mapping[str, object] = "fake",
    limit: Optional[int] = None,
    dry_run: bool = False,
    fail_fast: bool = False,
    energy_resume_success_ids: Optional[set[str] | frozenset[str]] = None,
    magnetism_resume_success_ids: Optional[set[str] | frozenset[str]] = None,
    energy_resume_success_predicate: Optional[Callable[[str], bool]] = None,
    magnetism_resume_success_predicate: Optional[Callable[[str], bool]] = None,
) -> EnrichmentReport:
    materialized = list(records)
    energy_report = None
    magnetism_report = None
    if run_energy:
        energy_report = run_energy_stage(
            materialized,
            backend=energy_backend,
            backend_selector=energy_backend_selector,
            limit=limit,
            dry_run=dry_run,
            fail_fast=fail_fast,
            resume_success_ids=energy_resume_success_ids,
            resume_success_predicate=energy_resume_success_predicate,
        )
    if run_magnetism:
        magnetism_report = run_magnetism_stage(
            materialized,
            backend=magnetism_backend,
            backend_selector=magnetism_backend_selector,
            limit=limit,
            dry_run=dry_run,
            fail_fast=fail_fast,
            resume_success_ids=magnetism_resume_success_ids,
            resume_success_predicate=magnetism_resume_success_predicate,
        )
    return EnrichmentReport(energy=energy_report, magnetism=magnetism_report)
