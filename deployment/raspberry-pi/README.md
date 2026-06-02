# RescueVision Edge — Raspberry Pi Deployment

RPi comparison benchmark for RescueVision Edge: runs TFLite FP32 and INT8 models, measures FPS, latency, RAM, and mAP.

## Setup

```bash
uv sync
```

## Run

```bash
# Run all benchmarks
uv run python src/benchmark.py

# Run detection on a single image or video
uv run python src/detect.py --model model/model_int8.tflite --image test.jpg

# Parse results
uv run python src/visualize.py --results results/
```

## Models

- `model/model_int8.tflite` — INT8 quantized (same as ESP32-S3)
- `model/model_fp32.tflite` — FP32 baseline (for comparison)
