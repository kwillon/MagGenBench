from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path(
    "tables/04_magnetic_screening/"
    "master_structures_with_enrichment_annotations.csv"
)

DEFAULT_OUTPUT = Path(
    "tables/04_magnetic_screening/"
    "phase5a4_batch10_annotations.csv"
)

LOADABLE_STATUSES = {"ok", "ok_with_warnings"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare deterministic Phase 5A-4 enrichment batch."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.limit <= 0:
        raise ValueError("--limit must be positive")

    with args.input.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    required = {
        "sample_uid",
        "structure_id",
        "cif_path",
        "status",
        "cif_load_status",
    }

    missing = required.difference(fieldnames)
    if missing:
        raise RuntimeError(
            f"Missing required columns: {sorted(missing)}"
        )

    selected = []
    seen_ids: set[str] = set()

    for row in rows:
        if row.get("status") != "validated":
            continue

        if row.get("cif_load_status") not in LOADABLE_STATUSES:
            continue

        structure_id = row.get("structure_id", "")
        sample_uid = row.get("sample_uid", "")

        if not structure_id:
            raise RuntimeError("Empty structure_id in eligible row")

        if sample_uid != structure_id:
            raise RuntimeError(
                f"sample_uid/structure_id mismatch: "
                f"{sample_uid!r} != {structure_id!r}"
            )

        if structure_id in seen_ids:
            raise RuntimeError(
                f"Duplicate structure_id: {structure_id}"
            )

        cif_path = Path(row.get("cif_path", ""))

        if not cif_path.is_file():
            raise FileNotFoundError(cif_path)

        seen_ids.add(structure_id)
        selected.append(row)

        if len(selected) >= args.limit:
            break

    if len(selected) != args.limit:
        raise RuntimeError(
            f"Requested {args.limit} rows, "
            f"selected {len(selected)}"
        )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = args.output.with_suffix(
        args.output.suffix + ".tmp"
    )

    with tmp.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(selected)

    tmp.replace(args.output)

    print("===== Phase 5A-4 batch manifest =====")
    print("source_rows:", len(rows))
    print("selected_rows:", len(selected))
    print("output:", args.output.resolve())

    print("\nselected:")
    for index, row in enumerate(selected):
        print(
            index,
            "|",
            row["structure_id"],
            "|",
            row.get("model_name", ""),
            "| magnetic:",
            row.get("magnetic_screening_status", ""),
            "| class:",
            row.get("compound_class_filter_status", ""),
            "|",
            row.get("formula_reduced", ""),
        )

    print("\nPHASE5A4_BATCH_MANIFEST: PASSED")


if __name__ == "__main__":
    main()
