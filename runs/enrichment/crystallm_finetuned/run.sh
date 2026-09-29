#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-/mnt/tank/scratch/kkapranova/MagGenBench-current}"

ENERGY_PY="${MAGGENBENCH_ENERGY_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python}"
MAG_PY="${MAGGENBENCH_MAGNETISM_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/enrichment"

MANIFEST=tables/04_magnetic_screening/phase5b_crystallm_finetuned_production_annotations.csv
ENERGY=tables/06_energy/phase5b_crystallm_finetuned_chgnet.csv
MAG=tables/07_magnetic_descriptors/phase5b_crystallm_finetuned_dxmag.csv
JOIN=tables/04_magnetic_screening/phase5b_crystallm_finetuned_joined.csv

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_orchestrator \
  --repo-root "$ROOT" \
  --energy-python "$ENERGY_PY" \
  --magnetism-python "$MAG_PY" \
  --checkpoint-every 25 \
  --cohort \
    "CrystaLLM-finetuned" \
    217 \
    "$MANIFEST" \
    "$ENERGY" \
    "$MAG" \
    "$JOIN" \
    "CHGNet — CrystaLLM fine-tuned" \
    "DXMag — CrystaLLM fine-tuned" \
    "Join — CrystaLLM fine-tuned" \
  --preflight-pass-label "CRYSTALLM_FT_ENRICHMENT_PREFLIGHT: PASSED" \
  --final-pass-label "CRYSTALLM_FT_ENRICHMENT: PASSED"
