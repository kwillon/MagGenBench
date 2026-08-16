#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa}"

ENERGY_PY="${MAGGENBENCH_ENERGY_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python}"
MAG_PY="${MAGGENBENCH_MAGNETISM_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/enrichment"

MG_MANIFEST=tables/04_magnetic_screening/crysjepa_base_production_annotations.csv
CDVAE_MANIFEST=tables/04_magnetic_screening/crysjepa_refined_production_annotations.csv

MG_ENERGY=tables/06_energy/crysjepa_base_chgnet.csv
CDVAE_ENERGY=tables/06_energy/crysjepa_refined_chgnet.csv

MG_MAG=tables/07_magnetic_descriptors/crysjepa_base_dxmag.csv
CDVAE_MAG=tables/07_magnetic_descriptors/crysjepa_refined_dxmag.csv

MG_JOIN=tables/04_magnetic_screening/crysjepa_base_joined.csv
CDVAE_JOIN=tables/04_magnetic_screening/crysjepa_refined_joined.csv

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_orchestrator \
  --repo-root "$ROOT" \
  --energy-python "$ENERGY_PY" \
  --magnetism-python "$MAG_PY" \
  --checkpoint-every 25 \
  --cohort "Crys-JEPA-Base" 1764 "$MG_MANIFEST" "$MG_ENERGY" "$MG_MAG" "$MG_JOIN" "CHGNet — Crys-JEPA Base" "DXMag — Crys-JEPA Base" "Join — Crys-JEPA Base" \
  --cohort "Crys-JEPA-Refined" 1543 "$CDVAE_MANIFEST" "$CDVAE_ENERGY" "$CDVAE_MAG" "$CDVAE_JOIN" "CHGNet — Crys-JEPA Refined" "DXMag — Crys-JEPA Refined" "Join — Crys-JEPA Refined" \
  --preflight-pass-label "PHASE5B_ENRICHMENT_PREFLIGHT: PASSED" \
  --final-pass-label "CRYSJEPA_ENRICHMENT: PASSED" \
  --require-energy-ok \
  --require-magnetism-ok
