#!/usr/bin/env bash
set -euo pipefail

ROOT="${MAGGENBENCH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OUTPUT_ROOT="${MAGGENBENCH_OUTPUT_ROOT:-reproduced/analysis_v2_magnetic}"

cd "$ROOT"

export PYTHONPATH="$ROOT/src"

python scripts/analysis/build_analysis_v2_magnetic.py \
  --standardized-enrichment tables/08_standardized_enrichment/standardized_enrichment.csv \
  --descriptor-v2 tables/09_descriptor_v2_magnetic/descriptor_v2_magnetic.csv \
  --output "$OUTPUT_ROOT/analysis_v2_magnetic.csv" "$@"
