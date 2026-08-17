#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
OUTPUT_ROOT="${MAGGENBENCH_OUTPUT_ROOT:-reproduced/descriptor_v2_magnetic}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src"

python scripts/descriptors/run_descriptor_v2_magnetic.py \
  --repo-root "$ROOT" \
  --input tables/08_standardized_enrichment/standardized_enrichment.csv \
  --output "$OUTPUT_ROOT/descriptor_v2_magnetic.csv" \
  --config config/descriptors_v2_magnetic.yaml "$@"
