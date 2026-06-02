# RescueVision Edge — ESP32-S3 Quantized Victim Detection

Research project: quantization-aware deployment of YOLO-based victim detection on ESP32-S3 for disaster SAR scenarios.

## Structure

```
training/          # ML training pipeline
  scripts/         # Training, quantization, evaluation
  configs/         # Experiment & dataset configs
  notebooks/       # Jupyter experiment reports
  dataset/         # Dataset (COCO person subset + SAR)
  baseline/        # FP32 baseline results
  quantized/       # INT8 quantized results

deployment/
  esp32-s3/        # TFLite Micro on ESP32-S3
  raspberry-pi/    # ONNX/TFLite on RPi (comparison)
```

## Prerequisites

- **uv** (fast Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **PlatformIO** (for ESP32-S3 builds): `uv pip install platformio` or `brew install platformio`

## Quick Start

```bash
# 1. Create venv & install dependencies
cd training
uv sync

# 2. Prepare dataset (COCO person subset)
uv run python scripts/01_prepare_dataset.py

# 3. Train FP32 baseline
uv run python scripts/02_train_baseline.py

# 4. Post-training quantization → INT8
uv run python scripts/03_quantize.py

# 5. Evaluate all variants (mAP, latency, size)
uv run python scripts/04_evaluate.py

# 6. Export model files for edge deployment
uv run python scripts/05_export_for_edge.py

# 7. Build & flash ESP32-S3
cd ../deployment/esp32-s3
pio run -t upload
```

## Experiment Overview

| Variant | Precision | Size | Platform |
|---------|-----------|------|----------|
| Baseline | FP32 | ~6 MB | PC (GPU) |
| TFLite FP32 | FP32 | ~6 MB | PC / RPi |
| TFLite INT8 | INT8 | ~2 MB | PC / RPi / ESP32-S3 |
| (Future) INT4 | INT4 | ~1 MB | ESP32-S3 |
