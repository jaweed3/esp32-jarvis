# RescueVision Edge — ESP32-S3 Deployment

TFLite Micro inference of INT8 quantized YOLOv8n for victim detection on ESP32-S3.

## Hardware Requirements

- Seeed Studio XIAO ESP32S3 Sense (or any ESP32-S3 with camera + PSRAM)
- OV2640 camera module (integrated on Sense board)
- USB-C cable for power + serial

## Build & Flash

```bash
# Install PlatformIO
pip install platformio   # or: brew install platformio

# Build & upload
pio run -t upload

# Monitor serial output
pio device monitor
```

## Memory Budget

| Component | Size | Location |
|-----------|------|----------|
| Model weights (INT8) | ~2 MB | Flash |
| Tensor arena | 2 MB | PSRAM |
| Frame buffer (320×240 RGB) | ~230 KB | PSRAM |
| Stack + misc | ~100 KB | SRAM |
| **Total flash** | ~3 MB | of 8 MB |
| **Total RAM** | ~2.4 MB | of 8 MB PSRAM + 512 KB SRAM |

## Output Format

Structured JSON per frame:
```json
{"t":12345,"inference_us":85000,"detections":[{"x1":10,"y1":20,"x2":100,"y2":200,"conf":0.85,"class":0}]}
```

## Experiment Protocol

1. Flash firmware
2. Run for 30 seconds (auto-stops)
3. Collect serial output → save to file
4. Parse with `python scripts/parse_benchmark.py`

## Results

See `training/evaluation_results/` for full benchmark data.
