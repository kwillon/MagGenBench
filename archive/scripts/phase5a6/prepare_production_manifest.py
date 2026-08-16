#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


LOADABLE_STATUSES = {
    "ok",
    "ok_with_warnings",
}


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Build the Phase 5A-6 production enrichment cohort "
            "from validated, loadable structures."
        )
    )
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise RuntimeError("Input CSV has no header.")

    selected = [
        r for r in rows
        if r.get("status") == "validated"
        and r.get("cif_load_status") in LOADABLE_STATUSES
    ]

    ids = [
        r.get("structure_id", "")
        for r in selected
    ]

    if not selected:
        raise RuntimeError(
            "Production cohort is empty."
        )

    if any(not sid for sid in ids):
        raise RuntimeError(
            "Empty structure_id in production cohort."
        )

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Duplicate structure_id in production cohort."
        )

    uid_mismatches = [
        r for r in selected
        if r.get("sample_uid") != r.get("structure_id")
    ]

    if uid_mismatches:
        raise RuntimeError(
            f"sample_uid/structure_id mismatches: "
            f"{len(uid_mismatches)}"
        )

    missing_cifs = [
        r for r in selected
        if not Path(r.get("cif_path", "")).is_file()
    ]

    if missing_cifs:
        raise RuntimeError(
            f"Missing CIF files: {len(missing_cifs)}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(selected)

    print("input_rows:", len(rows))
    print("production_rows:", len(selected))
    print("unique_structure_ids:", len(set(ids)))
    print("sample_uid_mismatch:", len(uid_mismatches))
    print("missing_cif:", len(missing_cifs))
    print("output:", output_path)
    print("PHASE5A6_PRODUCTION_MANIFEST: PASSED")


if __name__ == "__main__":
    main()
