#!/usr/bin/env bash
exec > /home/labti/pipeline_real.log 2>&1
set -x
date

cd /home/labti/esp32/training

echo === STEP 2: TRAIN ===
/home/labti/.local/bin/uv run python scripts/02_train_baseline.py
echo === TRAIN EXIT: $? ===

echo === STEP 3: QUANTIZE ===
/home/labti/.local/bin/uv run python scripts/03_quantize.py
echo === QUANTIZE EXIT: $? ===

echo === STEP 4: EVALUATE ===
/home/labti/.local/bin/uv run python scripts/04_evaluate.py
echo === EVALUATE EXIT: $? ===

echo === STEP 5: EXPORT ===
/home/labti/.local/bin/uv run python scripts/05_export_for_edge.py
echo === EXPORT EXIT: $? ===

echo === STEP 6: PAPER ===
/home/labti/.local/bin/uv run python scripts/06_generate_paper_artifacts.py
echo === PAPER EXIT: $? ===

echo === STEP 7: POWER ===
/home/labti/.local/bin/uv run python scripts/07_power_estimation.py
echo === POWER EXIT: $? ===

date
echo === PIPELINE DONE ===
