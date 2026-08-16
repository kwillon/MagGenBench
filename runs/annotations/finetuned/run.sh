#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench
PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python

cd "$ROOT"
export PYTHONPATH="$ROOT/src"

echo "============================================================"
echo "MatterGen fine-tuned"
echo "============================================================"

"$PY" scripts/annotations/prepare_finetuned_annotations.py \
  --cohort mattergen-finetuned \
  --repo-root "$ROOT"

"$PY" scripts/annotations/prepare_production_manifest.py \
  --input tables/04_magnetic_screening/phase5b_mattergen_finetuned_enrichment_annotations.csv \
  --output tables/04_magnetic_screening/phase5b_mattergen_finetuned_production_annotations.csv


echo
echo "============================================================"
echo "Con-CDVAE fine-tuned"
echo "============================================================"

"$PY" scripts/annotations/prepare_finetuned_annotations.py \
  --cohort concdvae-finetuned \
  --repo-root "$ROOT"

"$PY" scripts/annotations/prepare_production_manifest.py \
  --input tables/04_magnetic_screening/phase5b_concdvae_finetuned_enrichment_annotations.csv \
  --output tables/04_magnetic_screening/phase5b_concdvae_finetuned_production_annotations.csv


echo
echo "============================================================"
echo "Final Phase 5B audit"
echo "============================================================"

"$PY" - <<'PY'
from pathlib import Path
from collections import Counter
import csv

ROOT = Path(
    "/mnt/tank/scratch/kkapranova/"
    "MagGenBench/MagGenBench"
)

cohorts = {
    "MatterGen-finetuned": {
        "enriched": ROOT / (
            "tables/04_magnetic_screening/"
            "phase5b_mattergen_finetuned_enrichment_annotations.csv"
        ),
        "production": ROOT / (
            "tables/04_magnetic_screening/"
            "phase5b_mattergen_finetuned_production_annotations.csv"
        ),
    },
    "Con-CDVAE-finetuned": {
        "enriched": ROOT / (
            "tables/04_magnetic_screening/"
            "phase5b_concdvae_finetuned_enrichment_annotations.csv"
        ),
        "production": ROOT / (
            "tables/04_magnetic_screening/"
            "phase5b_concdvae_finetuned_production_annotations.csv"
        ),
    },
}

for name, paths in cohorts.items():
    print()
    print(name)

    with paths["enriched"].open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        enriched = list(csv.DictReader(f))

    with paths["production"].open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        production = list(csv.DictReader(f))

    if len(enriched) != 2000:
        raise RuntimeError(
            f"{name}: expected 2000 enriched rows, "
            f"got {len(enriched)}"
        )

    load_status = Counter(
        (r.get("cif_load_status") or "").strip()
        for r in enriched
    )

    source_status = Counter(
        (r.get("status") or "").strip()
        for r in enriched
    )

    ids = [
        (r.get("structure_id") or "").strip()
        for r in production
    ]

    uids = [
        (r.get("sample_uid") or "").strip()
        for r in production
    ]

    if not production:
        raise RuntimeError(f"{name}: empty production cohort")

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"{name}: duplicate production structure_id"
        )

    if ids != uids:
        raise RuntimeError(
            f"{name}: sample_uid != structure_id"
        )

    missing = [
        r.get("cif_path", "")
        for r in production
        if not Path(r.get("cif_path", "")).is_file()
    ]

    if missing:
        raise RuntimeError(
            f"{name}: missing production CIFs: {len(missing)}"
        )

    print("  enrichment_rows:", len(enriched))
    print("  source_status:", dict(source_status))
    print("  cif_load_status:", dict(load_status))
    print("  production_rows:", len(production))
    print("  unique_structure_id:", len(set(ids)))
    print("  missing_cif:", len(missing))

print()
print("PHASE5B_FINETUNED_ANNOTATIONS: PASSED")
PY
