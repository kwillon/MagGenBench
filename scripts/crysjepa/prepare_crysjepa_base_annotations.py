#!/usr/bin/env python3

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "legacy"))

from add_compound_class import classify_formula
from mvpipeline.pipeline.enrichment_annotations import (
    run_enrichment_annotations,
)


INPUT = ROOT / "outputs/crysjepa_base/all_structures.csv"

ADAPTED = (
    ROOT
    / "tables/03_features"
    / "crysjepa_base_with_classes.csv"
)

ENRICHED = (
    ROOT
    / "tables/04_magnetic_screening"
    / "crysjepa_base_enrichment_annotations.csv"
)

EXPECTED_TOTAL = 2000


with INPUT.open(
    encoding="utf-8-sig",
    newline="",
) as f:
    rows = list(csv.DictReader(f))


if len(rows) != EXPECTED_TOTAL:
    raise RuntimeError(
        f"Expected {EXPECTED_TOTAL} MVP rows, got {len(rows)}"
    )


adapted = []
seen = set()

for row in rows:
    source_id = row["structure_id"].strip()

    if not source_id:
        raise RuntimeError("Empty MVP structure_id")

    # Use a cohort-specific stable ID.
    stem = Path(source_id).stem
    sample_uid = stem

    if sample_uid in seen:
        raise RuntimeError(
            f"Duplicate sample_uid: {sample_uid}"
        )

    seen.add(sample_uid)

    cif_path = (ROOT / row["input_path"]).resolve()

    if not cif_path.is_file():
        raise FileNotFoundError(cif_path)

    formula = row.get("reduced_formula", "").strip()

    out = {
        "sample_uid": sample_uid,
        "model_name": "Crys-JEPA-Base",
        "model_short": "crysjepa_base",
        "run_uid": (
            "crysjepa_base_mp20_release_"
            "seed17_bench2000"
        ),
        "source_sample_id": source_id,
        "cif_path": str(cif_path),
        "cif_file_name": cif_path.name,
        "formula_reduced": formula,
        "formula_full": "",
        "status": row.get("status", ""),
        "status_source": "mvp_all_structures",
        "rejection_reason": row.get(
            "rejection_reason",
            "",
        ),
        "compound_class": classify_formula(formula),
        "cif_path_original": row["input_path"],
        "cif_exists": True,

        # Preserve MVP values explicitly as provenance.
        "mvp_is_suspicious": row.get(
            "is_suspicious",
            "",
        ),
        "mvp_is_duplicate": row.get(
            "is_duplicate",
            "",
        ),
        "mvp_is_novel": row.get(
            "is_novel",
            "",
        ),
        "mvp_is_magnetic": row.get(
            "is_magnetic",
            "",
        ),
        "mvp_n_atoms": row.get(
            "n_atoms",
            "",
        ),
        "mvp_density": row.get(
            "density",
            "",
        ),
        "mvp_volume_per_atom": row.get(
            "volume_per_atom",
            "",
        ),
        "mvp_spacegroup": row.get(
            "spacegroup",
            "",
        ),
        "mvp_min_distance": row.get(
            "min_distance",
            "",
        ),
        "mvp_charge_solution_json": row.get(
            "charge_solution_json",
            "",
        ),
        "mvp_details_json": row.get(
            "details_json",
            "",
        ),
    }

    adapted.append(out)


ADAPTED.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with ADAPTED.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(adapted[0]),
    )
    writer.writeheader()
    writer.writerows(adapted)


status_counts = {}
class_counts = {}

for row in adapted:
    status = row["status"]
    cls = row["compound_class"]

    status_counts[status] = (
        status_counts.get(status, 0) + 1
    )
    class_counts[cls] = (
        class_counts.get(cls, 0) + 1
    )


print("===== adapted MVP manifest =====")
print("rows:", len(adapted))
print("unique_sample_uid:", len(seen))
print("status:", status_counts)
print("output:", ADAPTED)

print()
print("compound_class:")
for key, value in sorted(
    class_counts.items(),
    key=lambda x: (-x[1], x[0]),
):
    print(f"  {key}: {value}")


report = run_enrichment_annotations(
    input_path=ADAPTED,
    output_path=ENRICHED,
    config_path=ROOT / "config/magnetism.yaml",
)


print()
print("===== canonical Phase 5A-1 =====")
print("input_count:", report.input_count)
print("output_count:", report.output_count)
print("output:", report.output_path)

if report.input_count != EXPECTED_TOTAL:
    raise RuntimeError(
        f"Unexpected enrichment input count: "
        f"{report.input_count}"
    )

if report.output_count != EXPECTED_TOTAL:
    raise RuntimeError(
        f"Unexpected enrichment output count: "
        f"{report.output_count}"
    )

print()
print("CRYSJEPA_BASE_ANNOTATIONS: PASSED")
