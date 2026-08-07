from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def csv_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    raise TypeError(f"Unsupported CSV value type: {type(value).__name__}")


def write_stage_csv_atomic(
    path: str | Path,
    records: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(output_path.name + ".tmp")
    try:
        with tmp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(fieldnames), extrasaction="ignore"
            )
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {key: csv_cell(record.get(key, "")) for key in fieldnames}
                )
        os.replace(tmp_path, output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return output_path


def read_stage_csv(path: str | Path) -> list[dict[str, str]]:
    input_path = Path(path)
    with input_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def merge_stage_records_for_resume(
    *,
    structure_ids: Sequence[str],
    previous_records: Iterable[Mapping[str, Any]],
    new_records: Iterable[Mapping[str, Any]],
    success_status: str = "ok",
) -> list[Mapping[str, Any]]:
    expected_ids = [str(value) for value in structure_ids]

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError(
            "Duplicate structure_id in expected structure IDs"
        )

    expected_set = set(expected_ids)

    def index_records(
        records: Iterable[Mapping[str, Any]],
        *,
        label: str,
    ) -> dict[str, Mapping[str, Any]]:
        indexed: dict[str, Mapping[str, Any]] = {}

        for record in records:
            structure_id = str(
                record.get("structure_id", "")
            )

            if not structure_id:
                raise ValueError(
                    f"{label} record has no structure_id"
                )

            if structure_id in indexed:
                raise ValueError(
                    f"Duplicate structure_id in {label}: "
                    f"{structure_id}"
                )

            indexed[structure_id] = record

        unknown = set(indexed) - expected_set
        if unknown:
            raise ValueError(
                f"Unexpected structure_id in {label}: "
                f"{sorted(unknown)}"
            )

        return indexed

    previous_by_id = index_records(
        previous_records,
        label="previous records",
    )
    new_by_id = index_records(
        new_records,
        label="new records",
    )

    merged: list[Mapping[str, Any]] = []

    for structure_id in expected_ids:
        previous = previous_by_id.get(structure_id)
        new = new_by_id.get(structure_id)

        if (
            previous is not None
            and previous.get("status") == success_status
        ):
            if new is not None:
                raise ValueError(
                    "Backend returned a new result for already "
                    f"successful structure_id: {structure_id}"
                )
            merged.append(previous)
            continue

        if new is None:
            raise ValueError(
                "No final result available for structure_id: "
                f"{structure_id}"
            )

        merged.append(new)

    return merged



def merge_stage_records_incremental(
    *,
    structure_ids: Sequence[str],
    previous_records: Iterable[Mapping[str, Any]],
    new_records: Iterable[Mapping[str, Any]],
    success_status: str = "ok",
) -> list[Mapping[str, Any]]:
    """Merge a resumable checkpoint while preserving manifest order.

    Existing successful rows are immutable. Existing failed rows may be
    replaced by new results. IDs not yet processed are allowed to be absent,
    which makes the result suitable for intermediate checkpoint files.
    """
    expected_ids = [str(value) for value in structure_ids]

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError(
            "Duplicate structure_id in expected structure IDs"
        )

    expected_set = set(expected_ids)

    def index_records(
        records: Iterable[Mapping[str, Any]],
        *,
        label: str,
    ) -> dict[str, Mapping[str, Any]]:
        indexed: dict[str, Mapping[str, Any]] = {}

        for record in records:
            structure_id = str(
                record.get("structure_id", "")
            )

            if not structure_id:
                raise ValueError(
                    f"{label} record has no structure_id"
                )

            if structure_id in indexed:
                raise ValueError(
                    f"Duplicate structure_id in {label}: "
                    f"{structure_id}"
                )

            if structure_id not in expected_set:
                raise ValueError(
                    f"Unexpected structure_id in {label}: "
                    f"{structure_id}"
                )

            indexed[structure_id] = record

        return indexed

    previous_by_id = index_records(
        previous_records,
        label="previous records",
    )
    new_by_id = index_records(
        new_records,
        label="new records",
    )

    merged = dict(previous_by_id)

    for structure_id, record in new_by_id.items():
        previous = previous_by_id.get(structure_id)

        if (
            previous is not None
            and previous.get("status") == success_status
        ):
            raise ValueError(
                "New result supplied for already successful "
                f"structure_id: {structure_id}"
            )

        merged[structure_id] = record

    return [
        merged[structure_id]
        for structure_id in expected_ids
        if structure_id in merged
    ]
