from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..io.stage_tables import write_stage_csv_atomic


ANNOTATION_KEY = "sample_uid"
RESULT_KEY = "structure_id"

ENERGY_PREFIX = "energy_"
MAGNETISM_PREFIX = "magnetism_"

ENERGY_JOIN_STATUS = "energy_join_status"
MAGNETISM_JOIN_STATUS = "magnetism_join_status"


@dataclass(frozen=True)
class EnrichmentResultsJoinReport:
    annotation_count: int
    energy_result_count: int
    magnetism_result_count: int
    energy_matched_count: int
    energy_missing_count: int
    magnetism_matched_count: int
    magnetism_missing_count: int
    energy_unmatched_result_count: int
    magnetism_unmatched_result_count: int
    output_count: int
    output_path: Path
    fieldnames: tuple[str, ...]


def _validate_fieldnames(
    fieldnames: Sequence[str],
    *,
    table_name: str,
) -> list[str]:
    fields = list(fieldnames)

    if not fields:
        raise ValueError(
            f"{table_name} has no CSV header"
        )

    empty = [
        index
        for index, field in enumerate(fields)
        if not str(field).strip()
    ]

    if empty:
        raise ValueError(
            f"{table_name} contains empty column names"
        )

    duplicates = sorted(
        {
            field
            for field in fields
            if fields.count(field) > 1
        }
    )

    if duplicates:
        raise ValueError(
            f"{table_name} contains duplicate columns: "
            f"{duplicates}"
        )

    return fields


def _materialize_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    fieldnames: Sequence[str],
    table_name: str,
) -> list[dict[str, Any]]:
    fields = set(fieldnames)
    materialized: list[dict[str, Any]] = []

    for position, source_row in enumerate(
        rows,
        start=1,
    ):
        row = dict(source_row)
        unknown = sorted(set(row).difference(fields))

        if unknown:
            raise ValueError(
                f"{table_name} row {position} contains "
                f"columns absent from its header: {unknown}"
            )

        missing = [
            field
            for field in fieldnames
            if field not in row
        ]

        if missing:
            raise ValueError(
                f"{table_name} row {position} is missing "
                f"columns: {missing}"
            )

        materialized.append(row)

    return materialized


def _read_csv_table(
    path: str | Path,
    *,
    table_name: str,
) -> tuple[list[dict[str, str]], list[str]]:
    source_path = Path(path)

    with source_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)

        fieldnames = _validate_fieldnames(
            reader.fieldnames or [],
            table_name=table_name,
        )

        rows: list[dict[str, str]] = []

        for line_number, source_row in enumerate(
            reader,
            start=2,
        ):
            if None in source_row:
                raise ValueError(
                    f"{table_name} line {line_number} "
                    "contains more values than the header"
                )

            if any(
                value is None
                for value in source_row.values()
            ):
                raise ValueError(
                    f"{table_name} line {line_number} "
                    "contains fewer values than the header"
                )

            rows.append(
                {
                    field: source_row[field]
                    for field in fieldnames
                }
            )

    return rows, fieldnames


def _key_value(
    row: Mapping[str, Any],
    *,
    key: str,
    table_name: str,
    position: int,
) -> str:
    raw_value = row.get(key)

    if raw_value is None:
        value = ""
    else:
        value = str(raw_value).strip()

    if not value:
        raise ValueError(
            f"{table_name} row {position} "
            f"has empty {key}"
        )

    return value


def _unique_index(
    rows: Sequence[Mapping[str, Any]],
    *,
    key: str,
    table_name: str,
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}

    for position, row in enumerate(rows, start=1):
        value = _key_value(
            row,
            key=key,
            table_name=table_name,
            position=position,
        )

        if value in index:
            raise ValueError(
                f"Duplicate {key} in "
                f"{table_name}: {value}"
            )

        index[value] = row

    return index


def _prefixed_fields(
    fieldnames: Sequence[str],
    *,
    prefix: str,
) -> list[str]:
    return [
        f"{prefix}{field}"
        for field in fieldnames
        if field != RESULT_KEY
    ]


def _validate_output_schema(
    annotation_fieldnames: Sequence[str],
    energy_fieldnames: Sequence[str],
    magnetism_fieldnames: Sequence[str],
) -> list[str]:
    additions = [
        ENERGY_JOIN_STATUS,
        *_prefixed_fields(
            energy_fieldnames,
            prefix=ENERGY_PREFIX,
        ),
        MAGNETISM_JOIN_STATUS,
        *_prefixed_fields(
            magnetism_fieldnames,
            prefix=MAGNETISM_PREFIX,
        ),
    ]

    duplicate_additions = sorted(
        {
            field
            for field in additions
            if additions.count(field) > 1
        }
    )

    if duplicate_additions:
        raise ValueError(
            "Namespaced output fields are not unique: "
            f"{duplicate_additions}"
        )

    collisions = sorted(
        set(annotation_fieldnames)
        .intersection(additions)
    )

    if collisions:
        raise ValueError(
            "Phase 5A-1 table already contains "
            "Phase 5A-2 output fields: "
            f"{collisions}"
        )

    return [
        *annotation_fieldnames,
        *additions,
    ]


def join_enrichment_result_rows(
    annotation_rows: Iterable[Mapping[str, Any]],
    *,
    annotation_fieldnames: Sequence[str],
    energy_rows: Iterable[Mapping[str, Any]],
    energy_fieldnames: Sequence[str],
    magnetism_rows: Iterable[Mapping[str, Any]],
    magnetism_fieldnames: Sequence[str],
    strict_result_ids: bool = True,
) -> tuple[list[dict[str, Any]], list[str]]:
    annotation_fields = _validate_fieldnames(
        annotation_fieldnames,
        table_name="Phase 5A-1 annotations",
    )

    energy_fields = _validate_fieldnames(
        energy_fieldnames,
        table_name="energy results",
    )

    magnetism_fields = _validate_fieldnames(
        magnetism_fieldnames,
        table_name="magnetism results",
    )

    for table_name, fields, required in (
        (
            "Phase 5A-1 annotations",
            annotation_fields,
            (ANNOTATION_KEY, RESULT_KEY),
        ),
        (
            "energy results",
            energy_fields,
            (RESULT_KEY,),
        ),
        (
            "magnetism results",
            magnetism_fields,
            (RESULT_KEY,),
        ),
    ):
        missing_required = [
            field
            for field in required
            if field not in fields
        ]

        if missing_required:
            raise ValueError(
                f"{table_name} is missing required "
                f"columns: {missing_required}"
            )

    annotations = _materialize_rows(
        annotation_rows,
        fieldnames=annotation_fields,
        table_name="Phase 5A-1 annotations",
    )

    energy = _materialize_rows(
        energy_rows,
        fieldnames=energy_fields,
        table_name="energy results",
    )

    magnetism = _materialize_rows(
        magnetism_rows,
        fieldnames=magnetism_fields,
        table_name="magnetism results",
    )

    annotation_index = _unique_index(
        annotations,
        key=ANNOTATION_KEY,
        table_name="Phase 5A-1 annotations",
    )

    energy_index = _unique_index(
        energy,
        key=RESULT_KEY,
        table_name="energy results",
    )

    magnetism_index = _unique_index(
        magnetism,
        key=RESULT_KEY,
        table_name="magnetism results",
    )

    for position, row in enumerate(
        annotations,
        start=1,
    ):
        sample_uid = _key_value(
            row,
            key=ANNOTATION_KEY,
            table_name="Phase 5A-1 annotations",
            position=position,
        )

        structure_id = _key_value(
            row,
            key=RESULT_KEY,
            table_name="Phase 5A-1 annotations",
            position=position,
        )

        if sample_uid != structure_id:
            raise ValueError(
                "Phase 5A-1 key mismatch at row "
                f"{position}: sample_uid={sample_uid!r}, "
                f"structure_id={structure_id!r}"
            )

    annotation_ids = set(annotation_index)
    unknown_energy_ids = sorted(
        set(energy_index).difference(annotation_ids)
    )
    unknown_magnetism_ids = sorted(
        set(magnetism_index).difference(annotation_ids)
    )

    if strict_result_ids and unknown_energy_ids:
        raise ValueError(
            "Energy result structure_id values are "
            "absent from Phase 5A-1 annotations: "
            f"{unknown_energy_ids[:10]}"
        )

    if strict_result_ids and unknown_magnetism_ids:
        raise ValueError(
            "Magnetism result structure_id values are "
            "absent from Phase 5A-1 annotations: "
            f"{unknown_magnetism_ids[:10]}"
        )

    output_fields = _validate_output_schema(
        annotation_fields,
        energy_fields,
        magnetism_fields,
    )

    energy_value_fields = [
        field
        for field in energy_fields
        if field != RESULT_KEY
    ]

    magnetism_value_fields = [
        field
        for field in magnetism_fields
        if field != RESULT_KEY
    ]

    output_rows: list[dict[str, Any]] = []

    for annotation_row in annotations:
        sample_uid = str(
            annotation_row[ANNOTATION_KEY]
        ).strip()

        energy_row = energy_index.get(sample_uid)
        magnetism_row = magnetism_index.get(sample_uid)

        output_row = dict(annotation_row)

        output_row[ENERGY_JOIN_STATUS] = (
            "matched"
            if energy_row is not None
            else "missing"
        )

        for field in energy_value_fields:
            output_row[f"{ENERGY_PREFIX}{field}"] = (
                energy_row[field]
                if energy_row is not None
                else ""
            )

        output_row[MAGNETISM_JOIN_STATUS] = (
            "matched"
            if magnetism_row is not None
            else "missing"
        )

        for field in magnetism_value_fields:
            output_row[
                f"{MAGNETISM_PREFIX}{field}"
            ] = (
                magnetism_row[field]
                if magnetism_row is not None
                else ""
            )

        output_rows.append(output_row)

    return output_rows, output_fields


def run_enrichment_results_join(
    *,
    annotations_path: str | Path,
    energy_results_path: str | Path,
    magnetism_results_path: str | Path,
    output_path: str | Path,
    strict_result_ids: bool = True,
) -> EnrichmentResultsJoinReport:
    annotations, annotation_fields = _read_csv_table(
        annotations_path,
        table_name="Phase 5A-1 annotations",
    )

    energy, energy_fields = _read_csv_table(
        energy_results_path,
        table_name="energy results",
    )

    magnetism, magnetism_fields = _read_csv_table(
        magnetism_results_path,
        table_name="magnetism results",
    )

    output_rows, output_fields = (
        join_enrichment_result_rows(
            annotations,
            annotation_fieldnames=annotation_fields,
            energy_rows=energy,
            energy_fieldnames=energy_fields,
            magnetism_rows=magnetism,
            magnetism_fieldnames=magnetism_fields,
            strict_result_ids=strict_result_ids,
        )
    )

    annotation_ids = {
        str(row[ANNOTATION_KEY]).strip()
        for row in annotations
    }

    energy_ids = {
        str(row[RESULT_KEY]).strip()
        for row in energy
    }

    magnetism_ids = {
        str(row[RESULT_KEY]).strip()
        for row in magnetism
    }

    written_path = write_stage_csv_atomic(
        output_path,
        output_rows,
        output_fields,
    )

    energy_matched = sum(
        row[ENERGY_JOIN_STATUS] == "matched"
        for row in output_rows
    )

    magnetism_matched = sum(
        row[MAGNETISM_JOIN_STATUS] == "matched"
        for row in output_rows
    )

    return EnrichmentResultsJoinReport(
        annotation_count=len(annotations),
        energy_result_count=len(energy),
        magnetism_result_count=len(magnetism),
        energy_matched_count=energy_matched,
        energy_missing_count=(
            len(output_rows) - energy_matched
        ),
        magnetism_matched_count=magnetism_matched,
        magnetism_missing_count=(
            len(output_rows) - magnetism_matched
        ),
        energy_unmatched_result_count=len(
            energy_ids.difference(annotation_ids)
        ),
        magnetism_unmatched_result_count=len(
            magnetism_ids.difference(annotation_ids)
        ),
        output_count=len(output_rows),
        output_path=written_path,
        fieldnames=tuple(output_fields),
    )
