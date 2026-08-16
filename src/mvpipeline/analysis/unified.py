from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from mvpipeline.descriptors.records import (
    DESCRIPTOR_RECORD_FIELDS,
    DESCRIPTOR_VALUE_FIELDS,
    IDENTITY_FIELDS,
    STATUS_FIELDS,
)
from mvpipeline.io.stage_tables import (
    read_stage_csv,
    write_stage_csv_atomic,
)


ANALYSIS_LABEL_FIELDS = [
    "analysis_cohort",
    "analysis_family",
    "analysis_state",
]

DOWNSTREAM_FIELDS = [
    "status",
    "status_source",
    "rejection_reason",
    "compound_class",
    "cif_load_status",
    "cif_warning_count",
    "cif_warnings",
    "contains_magnetic_element",
    "magnetic_elements",
    "magnetic_element_species_count",
    "magnetic_element_site_count",
    "contains_3d",
    "contains_4f",
    "nonmagnetic_by_composition_heuristic",
    "magnetic_screening_status",
    "magnetic_screening_reason",
    "compound_class_filter_status",
    "compound_class_filter_reason",
    "energy_status",
    "energy_error_code",
    "energy_error_message",
    "energy_backend",
    "energy_model_name",
    "energy_energy_unit",
    "energy_total_energy_eV",
    "energy_total_energy_eV_per_atom",
    "magnetism_status",
    "magnetism_error_code",
    "magnetism_error_message",
    "magnetism_backend",
    "magnetism_model_name",
    "magnetism_predicted_moment_value",
    "magnetism_moment_unit",
    "magnetism_moment_normalization",
    "magnetism_uncertainty_proxy",
    "magnetism_confidence_score",
    "magnetism_risk_level",
]

UNIFIED_ANALYSIS_FIELDS = [
    *IDENTITY_FIELDS,
    *ANALYSIS_LABEL_FIELDS,
    *DESCRIPTOR_VALUE_FIELDS,
    *STATUS_FIELDS,
    *DOWNSTREAM_FIELDS,
]

PROVENANCE_MATCH_FIELDS = [
    "model_name",
    "model_short",
    "run_uid",
    "source_sample_id",
]


@dataclass(frozen=True)
class AnalysisCohortSpec:
    analysis_cohort: str
    analysis_family: str | None
    analysis_state: str
    descriptor_path: Path
    joined_path: Path


@dataclass(frozen=True)
class UnifiedAnalysisReport:
    cohort_count: int
    input_descriptor_rows: int
    input_joined_rows: int
    output_rows: int
    output_path: Path


def _require_fields(
    rows: Sequence[Mapping[str, str]],
    *,
    required: Sequence[str],
    label: str,
) -> None:
    if not rows:
        raise ValueError(f"{label} is empty")

    missing = sorted(set(required) - set(rows[0]))
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def _index_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    label: str,
) -> tuple[list[str], dict[str, Mapping[str, str]]]:
    ordered_ids: list[str] = []
    indexed: dict[str, Mapping[str, str]] = {}

    for row in rows:
        sample_uid = (row.get("sample_uid") or "").strip()
        structure_id = (row.get("structure_id") or "").strip()

        if not sample_uid:
            raise ValueError(f"{label} row has empty sample_uid")
        if sample_uid != structure_id:
            raise ValueError(
                f"{label} sample_uid/structure_id mismatch: "
                f"{sample_uid!r}"
            )
        if sample_uid in indexed:
            raise ValueError(
                f"Duplicate sample_uid in {label}: {sample_uid}"
            )

        ordered_ids.append(sample_uid)
        indexed[sample_uid] = row

    return ordered_ids, indexed


def build_cohort_analysis_rows(
    descriptor_rows: Sequence[Mapping[str, str]],
    joined_rows: Sequence[Mapping[str, str]],
    *,
    analysis_cohort: str,
    analysis_family: str | None,
    analysis_state: str,
) -> list[dict[str, str]]:
    _require_fields(
        descriptor_rows,
        required=DESCRIPTOR_RECORD_FIELDS,
        label=f"{analysis_cohort} descriptor rows",
    )
    _require_fields(
        joined_rows,
        required=[*IDENTITY_FIELDS, *DOWNSTREAM_FIELDS],
        label=f"{analysis_cohort} joined rows",
    )

    descriptor_ids, descriptor_by_id = _index_rows(
        descriptor_rows,
        label=f"{analysis_cohort} descriptor rows",
    )
    _, joined_by_id = _index_rows(
        joined_rows,
        label=f"{analysis_cohort} joined rows",
    )

    descriptor_set = set(descriptor_by_id)
    joined_set = set(joined_by_id)
    if descriptor_set != joined_set:
        descriptor_only = sorted(descriptor_set - joined_set)
        joined_only = sorted(joined_set - descriptor_set)
        raise ValueError(
            f"{analysis_cohort} UID sets differ: "
            f"descriptor_only={descriptor_only[:5]}, "
            f"joined_only={joined_only[:5]}"
        )

    output: list[dict[str, str]] = []

    for sample_uid in descriptor_ids:
        descriptor = descriptor_by_id[sample_uid]
        joined = joined_by_id[sample_uid]

        for field in PROVENANCE_MATCH_FIELDS:
            descriptor_value = descriptor.get(field) or ""
            joined_value = joined.get(field) or ""
            if descriptor_value != joined_value:
                raise ValueError(
                    f"{analysis_cohort} provenance mismatch "
                    f"for {sample_uid}: {field} "
                    f"descriptor={descriptor_value!r} "
                    f"joined={joined_value!r}"
                )

        resolved_family = analysis_family
        if resolved_family is None:
            resolved_family = (descriptor.get("model_name") or "").strip()
        if not resolved_family:
            raise ValueError(
                f"{analysis_cohort} empty analysis_family for {sample_uid}"
            )

        record = {
            field: descriptor.get(field, "")
            for field in IDENTITY_FIELDS
        }
        record.update(
            {
                "analysis_cohort": analysis_cohort,
                "analysis_family": resolved_family,
                "analysis_state": analysis_state,
            }
        )
        record.update(
            {
                field: descriptor.get(field, "")
                for field in [
                    *DESCRIPTOR_VALUE_FIELDS,
                    *STATUS_FIELDS,
                ]
            }
        )
        record.update(
            {
                field: joined.get(field, "")
                for field in DOWNSTREAM_FIELDS
            }
        )
        output.append(record)

    if len(output) != len(descriptor_rows):
        raise RuntimeError(
            f"{analysis_cohort} row preservation failed: "
            f"{len(descriptor_rows)} -> {len(output)}"
        )

    return output


def run_unified_analysis(
    *,
    cohorts: Sequence[AnalysisCohortSpec],
    output_path: str | Path,
) -> UnifiedAnalysisReport:
    if not cohorts:
        raise ValueError("At least one analysis cohort is required")

    all_rows: list[dict[str, str]] = []
    global_ids: set[str] = set()
    descriptor_total = 0
    joined_total = 0

    for spec in cohorts:
        descriptor_rows = read_stage_csv(spec.descriptor_path)
        joined_rows = read_stage_csv(spec.joined_path)

        descriptor_total += len(descriptor_rows)
        joined_total += len(joined_rows)

        cohort_rows = build_cohort_analysis_rows(
            descriptor_rows,
            joined_rows,
            analysis_cohort=spec.analysis_cohort,
            analysis_family=spec.analysis_family,
            analysis_state=spec.analysis_state,
        )

        cohort_ids = {
            row["sample_uid"]
            for row in cohort_rows
        }
        overlap = global_ids & cohort_ids
        if overlap:
            raise ValueError(
                "sample_uid overlap across cohorts: "
                f"{sorted(overlap)[:5]}"
            )

        global_ids.update(cohort_ids)
        all_rows.extend(cohort_rows)

    if (
        len(all_rows) != descriptor_total
        or len(all_rows) != joined_total
    ):
        raise RuntimeError(
            "Unified analysis row preservation failed: "
            f"descriptor={descriptor_total}, "
            f"joined={joined_total}, "
            f"output={len(all_rows)}"
        )

    written_path = write_stage_csv_atomic(
        output_path,
        all_rows,
        UNIFIED_ANALYSIS_FIELDS,
    )

    return UnifiedAnalysisReport(
        cohort_count=len(cohorts),
        input_descriptor_rows=descriptor_total,
        input_joined_rows=joined_total,
        output_rows=len(all_rows),
        output_path=written_path,
    )
