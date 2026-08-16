from __future__ import annotations

from pathlib import Path

from pymatgen.core import Structure

from mvpipeline.pipeline.stage_common import PreparedStructureRecord


def prepare_records(
    rows: list[dict[str, str]],
    *,
    source: str,
) -> list[PreparedStructureRecord]:
    prepared: list[PreparedStructureRecord] = []

    for order, row in enumerate(rows):
        cif_path = Path(row["cif_path"])

        if not cif_path.is_file():
            raise FileNotFoundError(cif_path)

        structure = Structure.from_file(cif_path)

        prepared.append(
            PreparedStructureRecord(
                structure_id=row["structure_id"],
                order=order,
                metadata={
                    "source": source,
                    "cif_path": str(cif_path),
                },
                structure=structure,
                n_atoms=len(structure),
                composition=dict(
                    structure.composition.get_el_amt_dict()
                ),
            )
        )

    return prepared


def status_summary(
    rows: list[dict[str, object]],
) -> tuple[int, int]:
    ok = sum(row.get("status") == "ok" for row in rows)
    error = sum(row.get("status") == "error" for row in rows)
    return ok, error
