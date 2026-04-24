#!/usr/bin/env bash

set -e  # остановить скрипт при любой ошибке

# -----------------------------------------------------------------------------
# Общая конфигурация
# -----------------------------------------------------------------------------

THRESHOLDS="config/thresholds.yaml"

# Список моделей
MODELS=(
  "mattergen"
  "concdvae"
  "crystalformer"
  "crystalllm"
)

# -----------------------------------------------------------------------------
# Запуски
# -----------------------------------------------------------------------------

for MODEL in "${MODELS[@]}"; do
  echo "=== ${MODEL} validation ==="

  INPUT_DIR="samples/${MODEL}_cifs"
  OUT_DIR="outputs/${MODEL}"
  TRAIN_REFERENCE="datasets/${MODEL}/train_reference.csv"

  mvp \
    --input-dir "$INPUT_DIR" \
    --out-dir "$OUT_DIR" \
    --train-reference "$TRAIN_REFERENCE" \
    --thresholds "$THRESHOLDS"

  echo ""
done

echo "=== Все проверки завершены ==="
