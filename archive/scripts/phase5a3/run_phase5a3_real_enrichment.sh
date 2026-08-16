#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

REPO_ROOT="$(
    cd -- "$SCRIPT_DIR/../.."
    pwd
)"

cd "$REPO_ROOT"

ENERGY_ENV="${ENERGY_ENV:-/mnt/tank/scratch/kkapranova/envs/maggenbench-energy}"
MAG_ENV="${MAG_ENV:-/mnt/tank/scratch/kkapranova/envs/maggenbench-magnetism}"
CONDA_BIN="${CONDA_BIN:-}"

if [[ -z "$CONDA_BIN" ]]; then
    CONDA_BIN="$(command -v conda || true)"
fi

if [[ -z "$CONDA_BIN" ]]; then
    echo "ERROR: conda executable not found" >&2
    exit 1
fi

for env_path in "$ENERGY_ENV" "$MAG_ENV"; do
    if [[ ! -x "$env_path/bin/python" ]]; then
        echo "ERROR: invalid conda environment: $env_path" >&2
        exit 1
    fi
done

DXMAG_ARTIFACT="models/magnetism/magmom_model_dxmag.pkl"

if [[ ! -f "$DXMAG_ARTIFACT" ]]; then
    echo "ERROR: DXMag artifact not found: $DXMAG_ARTIFACT" >&2
    exit 1
fi

echo "===== Phase 5A-3 real enrichment smoke run ====="
echo "repository: $REPO_ROOT"
echo "energy environment: $ENERGY_ENV"
echo "magnetism environment: $MAG_ENV"

echo
echo "===== 1/3 Real CHGNet energy ====="

PYTHONPATH="$REPO_ROOT/src" \
"$CONDA_BIN" run \
    --prefix "$ENERGY_ENV" \
    --no-capture-output \
    python scripts/phase5a3/run_one_real_chgnet.py

echo
echo "===== 2/3 Real DXMag magnetism ====="

PYTHONPATH="$REPO_ROOT/src" \
"$CONDA_BIN" run \
    --prefix "$MAG_ENV" \
    --no-capture-output \
    python scripts/phase5a3/run_one_real_dxmag.py

echo
echo "===== 3/3 Strict enrichment join ====="

PYTHONPATH="$REPO_ROOT/src" \
"$CONDA_BIN" run \
    --prefix "$MAG_ENV" \
    --no-capture-output \
    python scripts/phase5a3/run_phase5a3_real_join.py

echo
echo "===== Phase 5A-3 completed ====="
echo "Energy output:"
echo "  tables/06_energy/phase5a3_chgnet_one_row.csv"
echo "Magnetism output:"
echo "  tables/07_magnetic_descriptors/phase5a3_dxmag_one_row.csv"
echo "Joined output:"
echo "  tables/04_magnetic_screening/phase5a3_real_enrichment_one_row.csv"
