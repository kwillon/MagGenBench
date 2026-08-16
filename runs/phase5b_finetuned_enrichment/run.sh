#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench

ENERGY_PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python
MAG_PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/phase5a4"

MG_MANIFEST=tables/04_magnetic_screening/phase5b_mattergen_finetuned_production_annotations.csv
CDVAE_MANIFEST=tables/04_magnetic_screening/phase5b_concdvae_finetuned_production_annotations.csv

MG_ENERGY=tables/06_energy/phase5b_mattergen_finetuned_chgnet.csv
CDVAE_ENERGY=tables/06_energy/phase5b_concdvae_finetuned_chgnet.csv

MG_MAG=tables/07_magnetic_descriptors/phase5b_mattergen_finetuned_dxmag.csv
CDVAE_MAG=tables/07_magnetic_descriptors/phase5b_concdvae_finetuned_dxmag.csv

MG_JOIN=tables/04_magnetic_screening/phase5b_mattergen_finetuned_joined.csv
CDVAE_JOIN=tables/04_magnetic_screening/phase5b_concdvae_finetuned_joined.csv


echo "============================================================"
echo "Pre-flight"
echo "============================================================"

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_checks preflight \
  --manifest "$MG_MANIFEST" 1376 \
  --manifest "$CDVAE_MANIFEST" 1299 \
  --pass-label "PHASE5B_ENRICHMENT_PREFLIGHT: PASSED"


echo
echo "============================================================"
echo "CHGNet — MatterGen fine-tuned"
echo "============================================================"

"$ENERGY_PY" scripts/phase5a4/run_batch_chgnet.py \
  --manifest "$MG_MANIFEST" \
  --output "$MG_ENERGY" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "CHGNet — Con-CDVAE fine-tuned"
echo "============================================================"

"$ENERGY_PY" scripts/phase5a4/run_batch_chgnet.py \
  --manifest "$CDVAE_MANIFEST" \
  --output "$CDVAE_ENERGY" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "DXMag — MatterGen fine-tuned"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_dxmag.py \
  --manifest "$MG_MANIFEST" \
  --output "$MG_MAG" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "DXMag — Con-CDVAE fine-tuned"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_dxmag.py \
  --manifest "$CDVAE_MANIFEST" \
  --output "$CDVAE_MAG" \
  --resume \
  --checkpoint-every 25


echo
echo "============================================================"
echo "Join — MatterGen fine-tuned"
echo "============================================================"

"$MAG_PY" scripts/phase5a4/run_batch_join.py \
  --annotations "$MG_MANIFEST" \
  --energy "$MG_ENERGY" \
  --magnetism "$MG_MAG" \
  --output "$MG_JOIN"


echo
echo "============================================================"
echo "Join — Con-CDVAE fine-tuned"
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

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_checks final-audit \
  --cohort "MatterGen-finetuned" 1376 "$MG_MANIFEST" "$MG_ENERGY" "$MG_MAG" "$MG_JOIN" \
  --cohort "Con-CDVAE-finetuned" 1299 "$CDVAE_MANIFEST" "$CDVAE_ENERGY" "$CDVAE_MAG" "$CDVAE_JOIN" \
  --pass-label "PHASE5B_FINETUNED_ENRICHMENT: PASSED"
