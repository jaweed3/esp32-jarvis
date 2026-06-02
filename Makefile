# RescueVision Edge — Makefile
# Usage: make <target>  (from project root)

UV = uv
PIO = pio
TRAINING = training
ESP32 = deployment/esp32-s3
RPI = deployment/raspberry-pi

# ──────────────────────────────────────
# Training pipeline
# ──────────────────────────────────────

.PHONY: install
install:            ## Install Python deps (uv sync)
	cd $(TRAINING) && $(UV) sync

.PHONY: dataset
dataset: install    ## Prepare COCO person dataset
	cd $(TRAINING) && $(UV) run python scripts/01_prepare_dataset.py

.PHONY: train
train: dataset      ## Train YOLOv8n FP32 baseline
	cd $(TRAINING) && $(UV) run python scripts/02_train_baseline.py

.PHONY: quantize
quantize: train     ## Post-training quantization FP32 → INT8
	cd $(TRAINING) && $(UV) run python scripts/03_quantize.py

.PHONY: evaluate
evaluate: quantize  ## Benchmark all variants across resolutions
	cd $(TRAINING) && $(UV) run python scripts/04_evaluate.py

.PHONY: export
export: evaluate    ## Export model for ESP32-S3 + RPi
	cd $(TRAINING) && $(UV) run python scripts/05_export_for_edge.py

.PHONY: all
all: export         ## Run full training pipeline (dataset→train→quantize→eval→export)

.PHONY: pipeline
pipeline: all       ## Alias for `all`

# ──────────────────────────────────────
# Individual steps (without dependency chain)
# ──────────────────────────────────────

.PHONY: dataset-only
dataset-only:       ## Prepare dataset only (skip install)
	cd $(TRAINING) && $(UV) run python scripts/01_prepare_dataset.py

.PHONY: train-only
train-only:         ## Train only (assumes dataset ready)
	cd $(TRAINING) && $(UV) run python scripts/02_train_baseline.py

.PHONY: quantize-only
quantize-only:      ## Quantize only (assumes trained model)
	cd $(TRAINING) && $(UV) run python scripts/03_quantize.py

.PHONY: eval-only
eval-only:          ## Evaluate only (assumes quantized model)
	cd $(TRAINING) && $(UV) run python scripts/04_evaluate.py

.PHONY: export-only
export-only:        ## Export only (assumes quantized model)
	cd $(TRAINING) && $(UV) run python scripts/05_export_for_edge.py

# ──────────────────────────────────────
# ESP32-S3 deployment
# ──────────────────────────────────────

ESP32_COMMON = -C $(ESP32)

.PHONY: esp32-build
esp32-build: export ## Build ESP32-S3 firmware
	$(PIO) $(ESP32_COMMON) run

.PHONY: esp32-upload
esp32-upload:       ## Upload firmware to ESP32-S3
	$(PIO) $(ESP32_COMMON) run -t upload

.PHONY: esp32-flash
esp32-flash: esp32-build esp32-upload  ## Build & flash (clean build)
	@echo "Done."

.PHONY: esp32-monitor
esp32-monitor:      ## Serial monitor
	$(PIO) $(ESP32_COMMON) device monitor

.PHONY: esp32-clean
esp32-clean:        ## Clean ESP32 build artifacts
	$(PIO) $(ESP32_COMMON) run --target clean

# ──────────────────────────────────────
# Raspberry Pi deployment
# ──────────────────────────────────────

.PHONY: rpi-install
rpi-install:        ## Install RPi deps
	cd $(RPI) && $(UV) sync

.PHONY: rpi-bench
rpi-bench: rpi-install export  ## Run RPi benchmark
	cd $(RPI) && $(UV) run python src/benchmark.py

.PHONY: rpi-viz
rpi-viz:            ## Generate RPi visualization charts
	cd $(RPI) && $(UV) run python src/visualize.py

# ──────────────────────────────────────
# Utilities
# ──────────────────────────────────────

.PHONY: notebook
notebook: install   ## Launch Jupyter notebook
	cd $(TRAINING) && $(UV) run jupyter notebook notebooks/

.PHONY: clean
clean:              ## Remove generated artifacts
	rm -rf $(TRAINING)/dataset/_raw/
	rm -rf $(TRAINING)/baseline/yolov8n_fp32/
	rm -f  $(TRAINING)/quantized/*.tflite
	rm -rf $(TRAINING)/evaluation_results/
	rm -f  $(TRAINING)/notebooks/*.png
	rm -rf $(RPI)/results/
	@echo "Cleaned generated artifacts."

.PHONY: distclean
distclean: clean    ## Remove everything including venv
	rm -rf $(TRAINING)/.venv/
	rm -rf $(RPI)/.venv/
	rm -rf .pio/
	@echo "Full clean done."

.PHONY: help
help:               ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
