from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from mvpipeline.pipeline.enrichment_results_join import (
    run_enrichment_results_join,
)


structure_id = (
    "cdvae__eval_gen_FM__eval_gen_FM0.pt__"
    "eval_gen_FM0_0000"
)

annotations_source = Path(
    "tables/04_magnetic_screening/"
    "master_structures_with_enrichment_annotations.csv"
)

annotations_one_row = Path(
    "/tmp/phase5a3_annotations_one_row.csv"
)

energy_path = Path(
    "tables/06_energy/"
    "phase5a3_chgnet_one_row.csv"
)

magnetism_path = Path(
    "tables/07_magnetic_descriptors/"
    "phase5a3_dxmag_one_row.csv"
)

output_path = Path(
    "tables/04_magnetic_screening/"
    "phase5a3_real_enrichment_one_row.csv"
)


# Extract exactly one Phase 5A-1 annotation row.
with annotations_source.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    reader = csv.DictReader(handle)
    annotation_fields = list(reader.fieldnames or [])
    matches = [
        row
        for row in reader
        if row.get("sample_uid") == structure_id
    ]

if len(matches) != 1:
    raise RuntimeError(
        f"Expected one annotation row, found {len(matches)}"
    )

annotation = matches[0]

if annotation.get("structure_id") != structure_id:
    raise RuntimeError(
        "Annotation sample_uid and structure_id differ"
    )

with annotations_one_row.open(
    "w",
    newline="",
    encoding="utf-8",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=annotation_fields,
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerow(annotation)


print("===== Strict Phase 5A-3 join =====")
print("structure_id:", structure_id)
print("annotations:", annotations_one_row)
print("energy:", energy_path)
print("magnetism:", magnetism_path)
print("output:", output_path)


report = run_enrichment_results_join(
    annotations_path=annotations_one_row,
    energy_results_path=energy_path,
    magnetism_results_path=magnetism_path,
    output_path=output_path,
    strict_result_ids=True,
)

print("\n===== Join report =====")
print(report)


with output_path.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    reader = csv.DictReader(handle)
    output_fields = list(reader.fieldnames or [])
    rows = list(reader)

if len(rows) != 1:
    raise RuntimeError(
        f"Expected one joined row, found {len(rows)}"
    )

row = rows[0]

if row.get("sample_uid") != structure_id:
    raise RuntimeError("Joined sample_uid is incorrect")

if row.get("structure_id") != structure_id:
    raise RuntimeError("Joined structure_id is incorrect")


result_fields = [
    field
    for field in output_fields
    if field not in annotation_fields
]

print("\n===== Joined result fields =====")
for field in result_fields:
    print(f"{field}: {row.get(field, '')}")


digest = hashlib.sha256(
    output_path.read_bytes()
).hexdigest()

print("\n===== Output validation =====")
print("annotation_column_count:", len(annotation_fields))
print("joined_column_count:", len(output_fields))
print("added_result_column_count:", len(result_fields))
print("row_count:", len(rows))
print("size_bytes:", output_path.stat().st_size)
print("sha256:", digest)

print("\nPHASE5A3_REAL_JOIN: PASSED")
