#!/usr/bin/env bash
set -euo pipefail

REPO=/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench
MVP=/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp

cd "$REPO"
export PYTHONPATH="$REPO/src"

"$MVP" \
  --input-dir samples/mattergen_finetuned_cifs \
  --out-dir outputs/mattergen_finetuned \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml \
  --model-name MatterGen-finetuned \
  --no-pretty
