#!/usr/bin/env bash
set -euo pipefail

REPO=/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa
MVP=/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp

cd "$REPO"
if [ -e outputs/crysjepa_refined ]; then echo "Refusing to overwrite outputs/crysjepa_refined" >&2; exit 1; fi
export PYTHONPATH="$REPO/src"

"$MVP" \
  --input-dir samples/crysjepa_refined_cifs \
  --out-dir outputs/crysjepa_refined \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml \
  --model-name Crys-JEPA-Refined \
  --no-pretty
