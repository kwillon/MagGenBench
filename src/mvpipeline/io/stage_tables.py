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
