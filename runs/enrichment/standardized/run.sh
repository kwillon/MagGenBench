#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-/mnt/tank/scratch/kkapranova/MagGenBench-current}"

ENERGY_PY="${MAGGENBENCH_ENERGY_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-energy/bin/python}"
MAG_PY="${MAGGENBENCH_MAGNETISM_PY:-/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python}"

OUTPUT_ROOT="${MAGGENBENCH_OUTPUT_ROOT:-reproduced/standardized_enrichment}"
CHECKPOINT_EVERY="${MAGGENBENCH_CHECKPOINT_EVERY:-25}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT/scripts/enrichment"

MANIFEST_DIR="$OUTPUT_ROOT/manifests"
ENERGY_DIR="$OUTPUT_ROOT/energy"
MAGNETISM_DIR="$OUTPUT_ROOT/magnetism"
JOINED_DIR="$OUTPUT_ROOT/joined"
MASTER_CSV="$OUTPUT_ROOT/standardized_enrichment.csv"
SHA_MANIFEST="$OUTPUT_ROOT/SHA256SUMS.txt"

mkdir -p "$ENERGY_DIR" "$MAGNETISM_DIR" "$JOINED_DIR"

"$MAG_PY" -m mvpipeline.enrichment.standardized prepare-manifests \
  --repo-root "$ROOT" \
  --output-dir "$MANIFEST_DIR"

"$MAG_PY" -m mvpipeline.pipeline.enrichment_run_orchestrator \
  --repo-root "$ROOT" \
  --energy-python "$ENERGY_PY" \
  --magnetism-python "$MAG_PY" \
  --checkpoint-every "$CHECKPOINT_EVERY" \
  --cohort "MatterGen-baseline" 1657 "$MANIFEST_DIR/mattergen_baseline.csv" "$ENERGY_DIR/mattergen_baseline_chgnet.csv" "$MAGNETISM_DIR/mattergen_baseline_dxmag.csv" "$JOINED_DIR/mattergen_baseline_joined.csv" "CHGNet - MatterGen baseline" "DXMag - MatterGen baseline" "Join - MatterGen baseline" \
  --cohort "MatterGen-finetuned" 1376 "$MANIFEST_DIR/mattergen_finetuned.csv" "$ENERGY_DIR/mattergen_finetuned_chgnet.csv" "$MAGNETISM_DIR/mattergen_finetuned_dxmag.csv" "$JOINED_DIR/mattergen_finetuned_joined.csv" "CHGNet - MatterGen fine-tuned" "DXMag - MatterGen fine-tuned" "Join - MatterGen fine-tuned" \
  --cohort "Con-CDVAE-baseline" 1864 "$MANIFEST_DIR/concdvae_baseline.csv" "$ENERGY_DIR/concdvae_baseline_chgnet.csv" "$MAGNETISM_DIR/concdvae_baseline_dxmag.csv" "$JOINED_DIR/concdvae_baseline_joined.csv" "CHGNet - Con-CDVAE baseline" "DXMag - Con-CDVAE baseline" "Join - Con-CDVAE baseline" \
  --cohort "Con-CDVAE-finetuned" 1299 "$MANIFEST_DIR/concdvae_finetuned.csv" "$ENERGY_DIR/concdvae_finetuned_chgnet.csv" "$MAGNETISM_DIR/concdvae_finetuned_dxmag.csv" "$JOINED_DIR/concdvae_finetuned_joined.csv" "CHGNet - Con-CDVAE fine-tuned" "DXMag - Con-CDVAE fine-tuned" "Join - Con-CDVAE fine-tuned" \
  --cohort "CrystalFormer-baseline" 1083 "$MANIFEST_DIR/crystalformer_baseline.csv" "$ENERGY_DIR/crystalformer_baseline_chgnet.csv" "$MAGNETISM_DIR/crystalformer_baseline_dxmag.csv" "$JOINED_DIR/crystalformer_baseline_joined.csv" "CHGNet - CrystalFormer baseline" "DXMag - CrystalFormer baseline" "Join - CrystalFormer baseline" \
  --cohort "CrystalFormer-finetuned" 1380 "$MANIFEST_DIR/crystalformer_finetuned.csv" "$ENERGY_DIR/crystalformer_finetuned_chgnet.csv" "$MAGNETISM_DIR/crystalformer_finetuned_dxmag.csv" "$JOINED_DIR/crystalformer_finetuned_joined.csv" "CHGNet - CrystalFormer fine-tuned" "DXMag - CrystalFormer fine-tuned" "Join - CrystalFormer fine-tuned" \
  --cohort "CrystaLLM-baseline" 98 "$MANIFEST_DIR/crystallm_baseline.csv" "$ENERGY_DIR/crystallm_baseline_chgnet.csv" "$MAGNETISM_DIR/crystallm_baseline_dxmag.csv" "$JOINED_DIR/crystallm_baseline_joined.csv" "CHGNet - CrystaLLM baseline" "DXMag - CrystaLLM baseline" "Join - CrystaLLM baseline" \
  --cohort "CrystaLLM-finetuned" 217 "$MANIFEST_DIR/crystallm_finetuned.csv" "$ENERGY_DIR/crystallm_finetuned_chgnet.csv" "$MAGNETISM_DIR/crystallm_finetuned_dxmag.csv" "$JOINED_DIR/crystallm_finetuned_joined.csv" "CHGNet - CrystaLLM fine-tuned" "DXMag - CrystaLLM fine-tuned" "Join - CrystaLLM fine-tuned" \
  --cohort "Crys-JEPA-Base" 1764 "$MANIFEST_DIR/crysjepa_base.csv" "$ENERGY_DIR/crysjepa_base_chgnet.csv" "$MAGNETISM_DIR/crysjepa_base_dxmag.csv" "$JOINED_DIR/crysjepa_base_joined.csv" "CHGNet - Crys-JEPA Base" "DXMag - Crys-JEPA Base" "Join - Crys-JEPA Base" \
  --cohort "Crys-JEPA-Refined" 1543 "$MANIFEST_DIR/crysjepa_refined.csv" "$ENERGY_DIR/crysjepa_refined_chgnet.csv" "$MAGNETISM_DIR/crysjepa_refined_dxmag.csv" "$JOINED_DIR/crysjepa_refined_joined.csv" "CHGNet - Crys-JEPA Refined" "DXMag - Crys-JEPA Refined" "Join - Crys-JEPA Refined" \
  --preflight-pass-label "STANDARDIZED_ENRICHMENT_PREFLIGHT: PASSED" \
  --final-pass-label "STANDARDIZED_ENRICHMENT_STAGES: PASSED" \
  --require-magnetism-ok

"$MAG_PY" -m mvpipeline.enrichment.standardized build-master \
  --joined-dir "$JOINED_DIR" \
  --output "$MASTER_CSV"

"$MAG_PY" -m mvpipeline.enrichment.standardized write-sha-manifest \
  --root "$OUTPUT_ROOT" \
  --output "$SHA_MANIFEST"

echo
echo "STANDARDIZED_ENRICHMENT: PASSED"
echo "output_root: $OUTPUT_ROOT"
echo "master: $MASTER_CSV"
echo "sha_manifest: $SHA_MANIFEST"
