from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import yaml
from pymatgen.core import Structure

from mvpipeline.energy.backends.chgnet import CHGNetBackend
from mvpipeline.energy.records import ENERGY_RECORD_FIELDS
from mvpipeline.io.stage_tables import write_stage_csv_atomic
from mvpipeline.pipeline.energy_stage import run_energy_stage
from mvpipeline.pipeline.stage_common import PreparedStructureRecord


structure_id = (
    "cdvae__eval_gen_FM__eval_gen_FM0.pt__"
    "eval_gen_FM0_0000"
)

annotations_path = Path(
    "tables/04_magnetic_screening/"
    "master_structures_with_enrichment_annotations.csv"
)

output_path = Path(
    "tables/06_energy/"
    "phase5a3_chgnet_one_row.csv"
)


with annotations_path.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    matches = [
        row
        for row in csv.DictReader(handle)
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

structure = Structure.from_file(cif_path)
composition = dict(
    structure.composition.get_el_amt_dict()
)

print("===== Real CHGNet input =====")
print("structure_id:", structure_id)
print("model_name:", annotation.get("model_name"))
print("formula:", structure.composition.formula)
print(
    "reduced_formula:",
    structure.composition.reduced_formula,
)
print("n_atoms:", len(structure))
print("cif_path:", cif_path)


with Path("config/energy.yaml").open(
    encoding="utf-8",
) as handle:
    settings = yaml.safe_load(handle)["energy"]["chgnet"]

backend = CHGNetBackend(
    model_name=settings["model_name"],
    model_selector=settings["model_selector"],
    device=settings["device"],
    output_semantics=settings["output_semantics"],
)

print("\n===== CHGNet settings =====")
print("configured_model_name:", settings["model_name"])
print("model_selector:", settings["model_selector"])
print(
    "resolved_checkpoint:",
    "0.3.0"
    if settings["model_selector"] == "default"
    else settings["model_selector"],
)
print("device:", settings["device"])
print("output_semantics:", settings["output_semantics"])


prepared = PreparedStructureRecord(
    structure_id=structure_id,
    order=0,
    metadata={
        "source": "phase5a3_real_chgnet_one_row",
        "cif_path": str(cif_path),
    },
    structure=structure,
    n_atoms=len(structure),
    composition=composition,
)

print("\n===== Running real CHGNet backend =====")

report = run_energy_stage(
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

result = rows[0]

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

written_path = write_stage_csv_atomic(
    output_path,
    rows,
    ENERGY_RECORD_FIELDS,
)

print("\n===== Real CHGNet result =====")

for field in ENERGY_RECORD_FIELDS:
    print(f"{field}: {result.get(field, '')}")

digest = hashlib.sha256(
    written_path.read_bytes()
).hexdigest()

print("\n===== Output =====")
print("path:", written_path.resolve())
print("size_bytes:", written_path.stat().st_size)
print("sha256:", digest)
print("row_count:", len(rows))

if result.get("status") != "ok":
    raise RuntimeError(
        "CHGNet did not return status=ok"
    )

print("\nREAL_CHGNET_ONE_ROW: PASSED")
