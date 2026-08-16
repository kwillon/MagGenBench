from __future__ import annotations

import csv
from pathlib import Path


def load_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise RuntimeError(f"Empty manifest: {path}")

    seen: set[str] = set()

    for row in rows:
        sample_uid = row.get("sample_uid", "")
        structure_id = row.get("structure_id", "")

        if not structure_id:
            raise RuntimeError("Empty structure_id")

        if sample_uid != structure_id:
            raise RuntimeError(
                f"sample_uid/structure_id mismatch: "
                f"{sample_uid!r} != {structure_id!r}"
            )

        if structure_id in seen:
            raise RuntimeError(
                f"Duplicate structure_id: {structure_id}"
            )

        seen.add(structure_id)

    return rows
