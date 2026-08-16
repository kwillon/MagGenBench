#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench}"

ENERGY_PY="${MAGGENBENCH_ENERGY_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python}"
MAG_PY="${MAGGENBENCH_MAGNETISM_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/enrichment"

MG_MANIFEST=tables/04_magnetic_screening/phase5b_mattergen_finetuned_production_annotations.csv
CDVAE_MANIFEST=tables/04_magnetic_screening/phase5b_concdvae_finetuned_production_annotations.csv

MG_ENERGY=tables/06_energy/phase5b_mattergen_finetuned_chgnet.csv
CDVAE_ENERGY=tables/06_energy/phase5b_concdvae_finetuned_chgnet.csv

MG_MAG=tables/07_magnetic_descriptors/phase5b_mattergen_finetuned_dxmag.csv
CDVAE_MAG=tables/07_magnetic_descriptors/phase5b_concdvae_finetuned_dxmag.csv

MG_JOIN=tables/04_magnetic_screening/phase5b_mattergen_finetuned_joined.csv
CDVAE_JOIN=tables/04_magnetic_screening/phase5b_concdvae_finetuned_joined.csv

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_orchestrator \
  --repo-root "$ROOT" \
  --energy-python "$ENERGY_PY" \
  --magnetism-python "$MAG_PY" \
  --checkpoint-every 25 \
  --cohort "MatterGen-finetuned" 1376 "$MG_MANIFEST" "$MG_ENERGY" "$MG_MAG" "$MG_JOIN" "CHGNet — MatterGen fine-tuned" "DXMag — MatterGen fine-tuned" "Join — MatterGen fine-tuned" \
  --cohort "Con-CDVAE-finetuned" 1299 "$CDVAE_MANIFEST" "$CDVAE_ENERGY" "$CDVAE_MAG" "$CDVAE_JOIN" "CHGNet — Con-CDVAE fine-tuned" "DXMag — Con-CDVAE fine-tuned" "Join — Con-CDVAE fine-tuned" \
  --preflight-pass-label "PHASE5B_ENRICHMENT_PREFLIGHT: PASSED" \
  --final-pass-label "PHASE5B_FINETUNED_ENRICHMENT: PASSED"
