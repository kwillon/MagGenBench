#!/usr/bin/env bash
#SBATCH --job-name=cllm-ft-enrich
#SBATCH --partition=aichem
#SBATCH --gres=gpu:a6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=runs/enrichment/crystallm_finetuned/logs/slurm-%j.out
#SBATCH --error=runs/enrichment/crystallm_finetuned/logs/slurm-%j.err

set -euo pipefail

ROOT=/mnt/tank/scratch/kkapranova/MagGenBench-current
cd "$ROOT"

echo "===== START ====="
date
hostname
nvidia-smi

echo
echo "===== INPUT ====="

PY=/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism/bin/python

"$PY" - <<'PY'
import csv
from pathlib import Path

p = Path(
    "tables/04_magnetic_screening/"
    "phase5b_crystallm_finetuned_production_annotations.csv"
)

with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print("manifest rows:", len(rows))
print("unique structure_id:", len({r["structure_id"] for r in rows}))

if len(rows) != 217:
    raise RuntimeError(f"Expected 217 rows, got {len(rows)}")
PY

echo
echo "===== ENRICHMENT ====="
date

MAGGENBENCH_ROOT="$ROOT" \
bash runs/enrichment/crystallm_finetuned/run.sh

echo
echo "===== FINISHED ====="
date
