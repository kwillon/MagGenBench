#!/usr/bin/env bash
set -euo pipefail

REPO="${MAGGENBENCH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
MVP="${MAGGENBENCH_MVP:-/nfs/home/kkapranova/anaconda3/envs/mvpipeline/bin/mvp}"
PY="${MAGGENBENCH_VALIDATION_PY:-${MVP%/mvp}/python}"

cd "$REPO"
export PYTHONPATH="$REPO/src"

"$PY" scripts/validation/run_validation.py \
  --cohort crystallm-finetuned \
  --repo-root "$REPO" \
  --mvp "$MVP"
