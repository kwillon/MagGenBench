#!/usr/bin/env bash
set -euo pipefail

REPO=/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa
MVP=/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp

cd "$REPO"
if [ -e outputs/crysjepa_base ]; then echo "Refusing to overwrite outputs/crysjepa_base" >&2; exit 1; fi
export PYTHONPATH="$REPO/src"

"$MVP" \
  --input-dir samples/crysjepa_base_cifs \
  --out-dir outputs/crysjepa_base \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml \
  --model-name Crys-JEPA-Base \
  --no-pretty
