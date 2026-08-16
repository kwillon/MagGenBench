#!/usr/bin/env bash
set -euo pipefail

REPO="${MAGGENBENCH_ROOT:-/mnt/tank/scratch/kkapranova/MagGenBench-crysjepa}"
MVP="${MAGGENBENCH_MVP:-/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp}"
PY="${MAGGENBENCH_VALIDATION_PY:-${MVP%/mvp}/python}"

cd "$REPO"
export PYTHONPATH="$REPO/src"

"$PY" scripts/validation/run_validation.py \
  --cohort crysjepa-refined \
  --repo-root "$REPO" \
  --mvp "$MVP"
