from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from pymatgen.core import Structure

from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.magnetism.backends.sklearn import (
    SklearnMagnetismBackend,
)
from mvpipeline.magnetism.config import (
    load_magnetism_config,
)
from mvpipeline.magnetism.records import (
    MAGNETISM_RECORD_FIELDS,
)
from mvpipeline.pipeline.magnetism_stage import (
    run_magnetism_stage,
)
from mvpipeline.pipeline.stage_common import (
    PreparedStructureRecord,
)


structure_id = (
    "cdvae__eval_gen_FM__eval_gen_FM0.pt__"
    "eval_gen_FM0_0000"
)

annotations_path = Path(
    "tables/04_magnetic_screening/"
    "master_structures_with_enrichment_annotations.csv"
)

output_path = Path(
    "tables/07_magnetic_descriptors/"
    "phase5a3_dxmag_one_row.csv"
)


with annotations_path.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    reader = csv.DictReader(handle)
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
        "sample_uid and structure_id do not match"
    )


cif_path = Path(annotation["cif_path"])

if not cif_path.is_file():
    raise FileNotFoundError(cif_path)


print("===== Real input =====")
print("structure_id:", structure_id)
print("model_name:", annotation.get("model_name"))
print("formula_reduced:", annotation.get("formula_reduced"))
print("cif_path:", cif_path)
print("cif_load_status:", annotation.get("cif_load_status"))
print(
    "magnetic_screening_status:",
    annotation.get("magnetic_screening_status"),
)


structure = Structure.from_file(cif_path)
composition = structure.composition.get_el_amt_dict()

print("\n===== Loaded structure =====")
print("formula:", structure.composition.formula)
print("reduced_formula:", structure.composition.reduced_formula)
print("n_sites:", len(structure))
print("composition:", composition)


config = load_magnetism_config(
    "config/magnetism.yaml"
)

backend = SklearnMagnetismBackend(
    settings=config.sklearn,
)

prepared = PreparedStructureRecord(
    structure_id=structure_id,
    order=0,
    metadata={
        "source": "phase5a3_real_dxmag_one_row",
        "cif_path": str(cif_path),
    },
    structure=structure,
    n_atoms=len(structure),
    composition=composition,
)


print("\n===== Running real DXMag backend =====")

report = run_magnetism_stage(
    [prepared],
    backend=backend,
    limit=1,
    fail_fast=True,
)

rows = list(report.records)

if len(rows) != 1:
    raise RuntimeError(
        f"Expected one result row, found {len(rows)}"
    )


output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

written_path = write_stage_csv_atomic(
    output_path,
    rows,
    MAGNETISM_RECORD_FIELDS,
)


result = rows[0]

print("\n===== Real DXMag result =====")

for field in MAGNETISM_RECORD_FIELDS:
    print(f"{field}: {result.get(field, '')}")


digest = hashlib.sha256(
    written_path.read_bytes()
).hexdigest()

print("\n===== Output =====")
print("path:", written_path.resolve())
print("size_bytes:", written_path.stat().st_size)
print("sha256:", digest)
print("row_count:", len(rows))

if result.get("error_code") or result.get("error_message"):
    raise RuntimeError(
        "DXMag returned a structured failure result"
    )

print("\nREAL_DXMAG_ONE_ROW: PASSED")
