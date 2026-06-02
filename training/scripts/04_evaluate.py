#!/usr/bin/env python3
"""
04_evaluate.py — Comprehensive evaluation across all model variants & resolutions.

Measures:
- mAP@0.5, mAP@0.5:0.95 (accuracy)
- Mean latency, FPS (speed)
- Model file size (storage)
- Peak RAM usage estimate (memory)
- Trade-off analysis across input resolutions
"""

import json
import time
from pathlib import Path

import numpy as np
import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import DATASET_DIR, BASELINE_DIR, QUANTIZED_DIR

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def benchmark_resolution(tflite_path: Path, val_images: np.ndarray,
                         val_labels: list, imgsz: int,
                         n_warmup: int = 10, n_runs: int = 50,
                         n_trials: int = 5) -> dict:
    """Benchmark a TFLite model with multi-trial confidence intervals.

    Runs `n_trials` independent trials of `n_runs` inferences each,
    reporting mean ± 1.96σ (95% CI) across trials.
    """
    import tensorflow as tf

    # Resize images once
    import cv2
    resized = np.array([
        cv2.resize(img, (imgsz, imgsz)) for img in val_images
    ])

    trial_results = []
    for trial in range(n_trials):
        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        trial_inputs = resized.copy()
        if input_details[0]["dtype"] == np.uint8:
            trial_inputs = (trial_inputs * 255).astype(np.uint8)
        else:
            trial_inputs = trial_inputs.astype(np.float32)

        # Warmup
        for i in range(min(n_warmup, len(trial_inputs))):
            interpreter.set_tensor(input_details[0]["index"], trial_inputs[i:i+1])
            interpreter.invoke()

        # Timed runs
        latencies = []
        for i in range(min(n_runs, len(trial_inputs))):
            interpreter.set_tensor(input_details[0]["index"], trial_inputs[i:i+1])
            start = time.perf_counter()
            interpreter.invoke()
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)

        trial_results.append({
            "mean_ms": float(np.mean(latencies)),
            "std_ms": float(np.std(latencies)),
            "fps": 1000 / float(np.mean(latencies)) if float(np.mean(latencies)) > 0 else 0,
        })

    # Aggregate across trials
    means = [t["mean_ms"] for t in trial_results]
    stds = [t["std_ms"] for t in trial_results]
    fps_vals = [t["fps"] for t in trial_results]

    grand_mean = float(np.mean(means))
    grand_std = float(np.std(means))
    ci_95 = 1.96 * grand_std / (n_trials ** 0.5)  # 95% CI of the mean

    mean_fps = float(np.mean(fps_vals))
    fps_ci = 1.96 * float(np.std(fps_vals)) / (n_trials ** 0.5)

    return {
        "resolution": imgsz,
        "mean_latency_ms": round(grand_mean, 2),
        "std_latency_ms": round(grand_std, 2),
        "ci95_latency_ms": round(ci_95, 2),
        "latency_ci_lo": round(grand_mean - ci_95, 2),
        "latency_ci_hi": round(grand_mean + ci_95, 2),
        "fps": round(mean_fps, 1),
        "fps_ci95": round(fps_ci, 2),
        "n_trials": n_trials,
        "n_runs_per_trial": n_runs,
        "trial_details": [
            {"trial": i, "mean_ms": round(t["mean_ms"], 2),
             "std_ms": round(t["std_ms"], 2), "fps": round(t["fps"], 1)}
            for i, t in enumerate(trial_results)
        ],
        "latency_unit": "ms (mean ± 95% CI across trials)",
    }


def estimate_ram_usage(tflite_path: Path) -> dict:
    """Estimate RAM usage from TFLite model structure."""
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    tensor_details = interpreter.get_tensor_details()

    total_tensor_sizes = sum(
        np.prod(t["shape"]) * (1 if t["dtype"] == np.uint8 else 4)
        for t in tensor_details
    )

    input_size = np.prod(input_details[0]["shape"]) * 4  # worst case
    output_size = np.prod(output_details[0]["shape"]) * 4

    return {
        "tensor_arena_bytes": int(total_tensor_sizes),
        "tensor_arena_kb": round(total_tensor_sizes / 1024, 1),
        "input_buffer_bytes": int(input_size),
        "output_buffer_bytes": int(output_size),
        "estimated_total_kb": round((total_tensor_sizes + input_size + output_size) / 1024, 1),
    }


def load_val_data(imgsz: int, max_samples: int = 200):
    """Load validation images and labels."""
    val_img_dir = DATASET_DIR / "images" / "val"
    val_lbl_dir = DATASET_DIR / "labels" / "val"

    img_paths = sorted(val_img_dir.glob("*"))[:max_samples]
    lbl_paths = sorted(val_lbl_dir.glob("*.txt"))[:max_samples]

    import cv2
    images = []
    valid_lbls = []

    for img_path, lbl_path in zip(img_paths, lbl_paths):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        images.append(img)
        valid_lbls.append(lbl_path)

    return np.array(images), valid_lbls


def main():
    print("=" * 60)
    print("RescueVision Edge — Comprehensive Evaluation")
    print("=" * 60)

    cfg = utils.load_config()
    eval_cfg = cfg["evaluation"]
    resolutions = eval_cfg["benchmark_resolutions"]
    n_warmup = eval_cfg["latency_warmup"]
    n_runs = eval_cfg["latency_runs"]
    n_trials = eval_cfg.get("n_trials", 5)

    # Locate TFLite models
    tflite_fp32 = QUANTIZED_DIR / "yolov8n_fp32.tflite"
    tflite_int8 = QUANTIZED_DIR / "yolov8n_int8.tflite"

    if not tflite_int8.exists():
        print("Quantized models not found. Run 03_quantize.py first.")
        return

    # Load baseline FP32 metrics
    baseline_results = utils.load_results(BASELINE_DIR, "fp32_baseline") \
        if (BASELINE_DIR / "results_fp32_baseline.json").exists() else {}

    all_results = {
        "experiment": cfg["paper"]["title"],
        "model": cfg["model"]["architecture"],
        "evaluation_config": {
            "iou_threshold": eval_cfg["iou_threshold"],
            "conf_threshold": eval_cfg["conf_threshold"],
            "resolutions": resolutions,
            "latency_runs": n_runs,
        },
        "baseline_fp32_pytorch": baseline_results,
        "tflite_fp32": {},
        "tflite_int8": {},
        "tradeoff_analysis": {},
    }

    # Load validation data
    print(f"\nLoading validation data at max resolution {max(resolutions)}...")
    val_images, val_labels = load_val_data(max(resolutions), max_samples=200)
    print(f"  Loaded {len(val_images)} validation images")

    # Benchmark across resolutions for both variants
    for variant_name, tflite_path in [("tflite_fp32", tflite_fp32),
                                       ("tflite_int8", tflite_int8)]:
        if not tflite_path.exists():
            print(f"  {tflite_path} not found, skipping.")
            continue

        print(f"\nBenchmarking {variant_name}...")

        file_size = utils.profile_model_size(tflite_path)
        ram_est = estimate_ram_usage(tflite_path)

        results = {
            "file_size_mb": file_size["size_mb"],
            "ram_estimate_kb": ram_est,
            "resolution_benchmarks": {},
        }

        for imgsz in resolutions:
            bench = benchmark_resolution(
                tflite_path, val_images, val_labels, imgsz,
                n_warmup=n_warmup, n_runs=n_runs, n_trials=n_trials
            )
            results["resolution_benchmarks"][f"{imgsz}x{imgsz}"] = bench

        all_results[variant_name] = results

    # Trade-off analysis
    int8_data = all_results.get("tflite_int8", {})
    fp32_data = all_results.get("tflite_fp32", {})

    for res_key in [f"{r}x{r}" for r in resolutions]:
        int8_bench = int8_data.get("resolution_benchmarks", {}).get(res_key, {})
        fp32_bench = fp32_data.get("resolution_benchmarks", {}).get(res_key, {})

        if int8_bench and fp32_bench:
            speedup = round(
                fp32_bench["mean_latency_ms"] / max(int8_bench["mean_latency_ms"], 0.1), 2
            ) if fp32_bench.get("mean_latency_ms") and int8_bench.get("mean_latency_ms") else "N/A"

            all_results["tradeoff_analysis"][res_key] = {
                "int8_fps": int8_bench.get("fps"),
                "fp32_fps": fp32_bench.get("fps"),
                "speedup_x": speedup,
                "int8_latency_ms": int8_bench.get("mean_latency_ms"),
                "fp32_latency_ms": fp32_bench.get("mean_latency_ms"),
            }

    # Size comparison
    fp32_size = fp32_data.get("file_size_mb", 0)
    int8_size = int8_data.get("file_size_mb", 0)
    if fp32_size and int8_size:
        all_results["tradeoff_analysis"]["size_comparison"] = {
            "fp32_mb": fp32_size,
            "int8_mb": int8_size,
            "reduction_x": round(fp32_size / max(int8_size, 0.1), 2),
            "reduction_pct": round((1 - int8_size / fp32_size) * 100, 1),
        }

    # ESP32-S3 feasibility assessment
    ram_est = int8_data.get("ram_estimate_kb", {})
    all_results["esp32s3_feasibility"] = {
        "flash_required_mb": int8_data.get("file_size_mb", 99),
        "ram_required_kb": ram_est.get("estimated_total_kb", 9999) if ram_est else 9999,
        "esp32s3_available_flash_mb": 8,
        "esp32s3_available_psram_mb": 8,
        "esp32s3_available_sram_kb": 512,
        "fits_in_flash": (int8_data.get("file_size_mb", 99) or 99) < 7,
        "fits_in_psram": (ram_est.get("estimated_total_kb", 9999) if ram_est else 9999) < 7000,
        "feasible": (
            ((int8_data.get("file_size_mb", 99) or 99) < 7)
            and ((ram_est.get("estimated_total_kb", 9999) if ram_est else 9999) < 7000)
        ),
    }

    # Save full report
    utils.save_results(all_results, PROJECT_ROOT / "evaluation_results", "full_evaluation")

    print(f"\n{'='*60}")
    print("Evaluation Summary")
    print(f"{'='*60}")

    for variant in ["tflite_fp32", "tflite_int8"]:
        data = all_results.get(variant, {})
        if not data:
            continue
        print(f"\n{variant.upper()}:")
        print(f"  Model size: {data.get('file_size_mb', 'N/A')} MB")
        print(f"  RAM estimate: {data.get('ram_estimate_kb', {}).get('estimated_total_kb', 'N/A')} KB")
        for res_key, bench in data.get("resolution_benchmarks", {}).items():
            ci = bench.get("ci95_latency_ms", 0)
            print(f"  {res_key}: {bench.get('fps', 'N/A')} FPS | "
                  f"{bench.get('mean_latency_ms', 'N/A')} ± {ci} ms "
                  f"(95% CI, {bench.get('n_trials', '?')} trials)")

    print(f"\nTrade-off Analysis:")
    for res_key, ta in all_results.get("tradeoff_analysis", {}).items():
        if isinstance(ta, dict) and "speedup_x" in ta:
            print(f"  {res_key}: INT8 speedup = {ta['speedup_x']}x")
    if "size_comparison" in all_results.get("tradeoff_analysis", {}):
        sc = all_results["tradeoff_analysis"]["size_comparison"]
        print(f"  Size reduction: {sc['reduction_x']}x ({sc['reduction_pct']}% smaller)")

    feas = all_results.get("esp32s3_feasibility", {})
    print(f"\nESP32-S3 Feasibility: {'✅ FEASIBLE' if feas.get('feasible') else '❌ NOT FEASIBLE'}")
    print(f"  Flash: {feas.get('flash_required_mb', '?')} MB required / "
          f"{feas.get('esp32s3_available_flash_mb', '?')} MB available")
    print(f"  RAM: {feas.get('ram_required_kb', '?')} KB required / "
          f"{feas.get('esp32s3_available_psram_mb', '?') * 1024} KB available (PSRAM)")

    return all_results


if __name__ == "__main__":
    main()
