#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa

ENERGY_PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python
MAG_PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/phase5a4"

MG_MANIFEST=tables/04_magnetic_screening/crysjepa_base_production_annotations.csv
CDVAE_MANIFEST=tables/04_magnetic_screening/crysjepa_refined_production_annotations.csv

MG_ENERGY=tables/06_energy/crysjepa_base_chgnet.csv
CDVAE_ENERGY=tables/06_energy/crysjepa_refined_chgnet.csv

MG_MAG=tables/07_magnetic_descriptors/crysjepa_base_dxmag.csv
CDVAE_MAG=tables/07_magnetic_descriptors/crysjepa_refined_dxmag.csv

MG_JOIN=tables/04_magnetic_screening/crysjepa_base_joined.csv
CDVAE_JOIN=tables/04_magnetic_screening/crysjepa_refined_joined.csv


echo "============================================================"
echo "Pre-flight"
echo "============================================================"

"$MAG_PY" - <<'PY'
from pathlib import Path
import csv

expected = {
    Path(
        "tables/04_magnetic_screening/"
        "crysjepa_base_production_annotations.csv"
    ): 1764,
    Path(
        "tables/04_magnetic_screening/"
        "crysjepa_refined_production_annotations.csv"
    ): 1543,
}

for path, expected_rows in expected.items():
    if not path.is_file():
        raise RuntimeError(f"Missing manifest: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    ids = [
        (row.get("structure_id") or "").strip()
        for row in rows
    ]

    if len(rows) != expected_rows:
        raise RuntimeError(
            f"{path}: expected {expected_rows} rows, got {len(rows)}"
        )

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"{path}: duplicate structure_id"
        )

    if any(not x for x in ids):
        raise RuntimeError(
            f"{path}: empty structure_id"
        )

    print(path)
    print("  rows:", len(rows))
    print("  unique_structure_id:", len(set(ids)))

print("PHASE5B_ENRICHMENT_PREFLIGHT: PASSED")
PY


echo
echo "============================================================"
echo "CHGNet — Crys-JEPA Base"
echo "============================================================"

"$ENERGY_PY" scripts/phase5a4/run_batch_chgnet.py \
  --manifest "$MG_MANIFEST" \
  --output "$MG_ENERGY" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "CHGNet — Crys-JEPA Refined"
echo "============================================================"

"$ENERGY_PY" scripts/phase5a4/run_batch_chgnet.py \
  --manifest "$CDVAE_MANIFEST" \
  --output "$CDVAE_ENERGY" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "DXMag — Crys-JEPA Base"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_dxmag.py \
  --manifest "$MG_MANIFEST" \
  --output "$MG_MAG" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "DXMag — Crys-JEPA Refined"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_dxmag.py \
  --manifest "$CDVAE_MANIFEST" \
  --output "$CDVAE_MAG" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "Join — Crys-JEPA Base"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_join.py \
  --annotations "$MG_MANIFEST" \
  --energy "$MG_ENERGY" \
  --magnetism "$MG_MAG" \
  --output "$MG_JOIN"


echo
echo "============================================================"
echo "Join — Crys-JEPA Refined"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_join.py \
  --annotations "$CDVAE_MANIFEST" \
  --energy "$CDVAE_ENERGY" \
  --magnetism "$CDVAE_MAG" \
  --output "$CDVAE_JOIN"


echo
echo "============================================================"
echo "Final audit"
echo "============================================================"

"$MAG_PY" - <<'PY'
from pathlib import Path
from collections import Counter
import csv

from mvpipeline.pipeline.stage_common import require_all_status_ok

cohorts = {
    "Crys-JEPA-Base": {
        "expected": 1764,
        "annotations": Path(
            "tables/04_magnetic_screening/"
            "crysjepa_base_production_annotations.csv"
        ),
        "energy": Path(
            "tables/06_energy/"
            "crysjepa_base_chgnet.csv"
        ),
        "magnetism": Path(
            "tables/07_magnetic_descriptors/"
            "crysjepa_base_dxmag.csv"
        ),
        "joined": Path(
            "tables/04_magnetic_screening/"
            "crysjepa_base_joined.csv"
        ),
    },
    "Crys-JEPA-Refined": {
        "expected": 1543,
        "annotations": Path(
            "tables/04_magnetic_screening/"
            "crysjepa_refined_production_annotations.csv"
        ),
        "energy": Path(
            "tables/06_energy/"
            "crysjepa_refined_chgnet.csv"
        ),
        "magnetism": Path(
            "tables/07_magnetic_descriptors/"
            "crysjepa_refined_dxmag.csv"
        ),
        "joined": Path(
            "tables/04_magnetic_screening/"
            "crysjepa_refined_joined.csv"
        ),
    },
}

def read_rows(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))

for name, cfg in cohorts.items():
    print()
    print(name)

    for key in [
        "annotations",
        "energy",
        "magnetism",
        "joined",
    ]:
        path = cfg[key]

        if not path.is_file():
            raise RuntimeError(
                f"{name}: missing {key}: {path}"
            )

        rows = read_rows(path)

        print(f"  {key}_rows:", len(rows))

        if len(rows) != cfg["expected"]:
            raise RuntimeError(
                f"{name}: {key} expected "
                f"{cfg['expected']} rows, got {len(rows)}"
            )

    energy = read_rows(cfg["energy"])
    magnetism = read_rows(cfg["magnetism"])
    joined = read_rows(cfg["joined"])

    energy_status = Counter(
        (r.get("status") or "").strip()
        for r in energy
    )

    magnetism_status = Counter(
        (r.get("status") or "").strip()
        for r in magnetism
    )

    require_all_status_ok(
        energy,
        expected_count=cfg["expected"],
        label=f"{name} energy",
    )

    require_all_status_ok(
        magnetism,
        expected_count=cfg["expected"],
        label=f"{name} magnetism",
    )

    joined_ids = [
        (r.get("structure_id") or "").strip()
        for r in joined
    ]

    print("  energy_status:", dict(energy_status))
    print("  magnetism_status:", dict(magnetism_status))
    print(
        "  unique_joined_structure_id:",
        len(set(joined_ids)),
    )

    if len(joined_ids) != len(set(joined_ids)):
        raise RuntimeError(
            f"{name}: duplicate joined structure_id"
        )

print()
print("CRYSJEPA_ENRICHMENT: PASSED")
PY
