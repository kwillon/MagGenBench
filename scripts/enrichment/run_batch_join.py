from __future__ import annotations

import argparse
import csv
from pathlib import Path

from mvpipeline.pipeline.enrichment_results_join import (
    run_enrichment_results_join,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Strict Phase 5A-4 enrichment batch join."
    )
    p.add_argument("--annotations", type=Path, required=True)
    p.add_argument("--energy", type=Path, required=True)
    p.add_argument("--magnetism", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def main() -> None:
    args = parse_args()

    annotation_fields, annotations = read_rows(args.annotations)

    if not annotations:
        raise RuntimeError("Annotation batch is empty")

    expected_ids = [row.get("structure_id", "") for row in annotations]

    if any(not structure_id for structure_id in expected_ids):
        raise RuntimeError("Empty structure_id in annotations")

    if len(set(expected_ids)) != len(expected_ids):
        raise RuntimeError("Duplicate structure_id in annotations")

    for row in annotations:
        if row.get("sample_uid") != row.get("structure_id"):
            raise RuntimeError(
                "Annotation sample_uid and structure_id differ"
            )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("===== Phase 5A-4 strict join =====")
    print("annotations:", args.annotations)
    print("energy:", args.energy)
    print("magnetism:", args.magnetism)
    print("output:", args.output)
    print("expected_rows:", len(annotations))

    report = run_enrichment_results_join(
        annotations_path=args.annotations,
        energy_results_path=args.energy,
        magnetism_results_path=args.magnetism,
        output_path=args.output,
        strict_result_ids=True,
    )

    output_fields, joined = read_rows(args.output)

    if len(joined) != len(annotations):
        raise RuntimeError(
            f"Expected {len(annotations)} joined rows, "
            f"got {len(joined)}"
        )

    joined_ids = [row.get("structure_id", "") for row in joined]

    if joined_ids != expected_ids:
        raise RuntimeError(
            "Joined structure_id order/content differs from annotations"
        )

    for row in joined:
        if row.get("sample_uid") != row.get("structure_id"):
            raise RuntimeError(
                "Joined sample_uid and structure_id differ"
            )

    result_fields = [
        field
        for field in output_fields
        if field not in annotation_fields
    ]

    print("\n===== Join report =====")
    print(report)

    print("\n===== Output validation =====")
    print("annotation_rows:", len(annotations))
    print("joined_rows:", len(joined))
    print("annotation_columns:", len(annotation_fields))
    print("joined_columns:", len(output_fields))
    print("added_result_columns:", len(result_fields))
    print("unique_structure_ids:", len(set(joined_ids)))

    print("\nPHASE5A4_BATCH_JOIN: PASSED")


if __name__ == "__main__":
    main()
