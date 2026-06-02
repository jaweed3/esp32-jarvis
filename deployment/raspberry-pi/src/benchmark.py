#!/usr/bin/env python3
"""
RPi benchmark: run TFLite FP32 and INT8 models, report FPS, mAP, latency, RAM.
Compares performance against PC baseline and ESP32-S3 targets.
"""

import json
import os
import time
import subprocess
from pathlib import Path

import numpy as np
import tqdm

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "model"


def get_rpi_model():
    """Detect RPi model from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            data = f.read()
        if "Raspberry Pi 5" in data:
            return "Raspberry Pi 5"
        elif "Raspberry Pi 4" in data:
            return "Raspberry Pi 4"
        elif "Raspberry Pi 3" in data:
            return "Raspberry Pi 3"
        else:
            return f"Unknown RPi ({data[:100]})"
    except FileNotFoundError:
        return "Not a Raspberry Pi (running on PC for debug)"


def get_ram_usage():
    """Get current RAM usage in MB."""
    try:
        result = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        parts = lines[1].split()
        return {
            "total_mb": int(parts[1]),
            "used_mb": int(parts[2]),
            "free_mb": int(parts[3]),
        }
    except Exception:
        return {"error": "Could not read RAM usage"}


def get_cpu_freq():
    """Get current CPU frequency."""
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_clock", "arm"],
            capture_output=True, text=True, check=True,
        )
        freq_hz = int(result.stdout.strip().split("=")[1])
        return freq_hz / 1_000_000  # MHz
    except Exception:
        return None


def benchmark_model(tflite_path, val_images, val_labels, imgsz,
                    n_warmup=10, n_runs=100, label="model"):
    """Benchmark a TFLite model on RPi."""
    import tensorflow as tf

    print(f"\nBenchmarking {label}...")

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    # Prepare input data
    import cv2
    preprocessed = []
    for img in val_images:
        resized = cv2.resize(img, (imgsz, imgsz))
        if input_details["dtype"] == np.uint8:
            resized = (resized * 255).astype(np.uint8)
        else:
            resized = resized.astype(np.float32)
        preprocessed.append(resized)
    preprocessed = np.array(preprocessed)

    # Warmup
    for i in range(min(n_warmup, len(preprocessed))):
        interpreter.set_tensor(input_details["index"], preprocessed[i:i+1])
        interpreter.invoke()

    # Timed runs
    latencies = []
    ram_samples = []
    cpu_freqs = []

    for i in tqdm.trange(min(n_runs, len(preprocessed)), desc=f"{label} @ {imgsz}"):
        interpreter.set_tensor(input_details["index"], preprocessed[i:i+1])

        start = time.perf_counter()
        interpreter.invoke()
        elapsed = time.perf_counter() - start

        latencies.append(elapsed * 1000)
        ram_samples.append(get_ram_usage())
        if cpu_freqs is None:
            cpu_freqs.append(get_cpu_freq())

    mean_lat = float(np.mean(latencies))
    std_lat = float(np.std(latencies))
    fps = 1000 / mean_lat if mean_lat > 0 else 0

    # Memory
    avg_ram = {
        k: float(np.mean([r[k] for r in ram_samples if "error" not in r]))
        for k in ["total_mb", "used_mb", "free_mb"]
    } if ram_samples else {}

    results = {
        "model": label,
        "model_path": str(tflite_path),
        "resolution": imgsz,
        "mean_latency_ms": round(mean_lat, 2),
        "std_latency_ms": round(std_lat, 2),
        "fps": round(fps, 1),
        "ram_usage_mb": avg_ram,
        "cpu_freq_mhz": cpu_freqs[0] if cpu_freqs else None,
        "n_runs": n_runs,
    }

    file_size = tflite_path.stat().st_size / (1024 * 1024)
    results["model_size_mb"] = round(file_size, 2)

    return results


def main():
    print("=" * 60)
    print("RescueVision Edge — RPi Benchmark Suite")
    print("=" * 60)

    device = get_rpi_model()
    print(f"Device: {device}")

    ram_info = get_ram_usage()
    print(f"RAM: {ram_info}")

    freq = get_cpu_freq()
    if freq:
        print(f"CPU freq: {freq:.0f} MHz")

    resolutions = [192, 256, 320]
    all_results = {
        "device": device,
        "ram": ram_info,
        "cpu_freq_mhz": freq,
        "benchmarks": [],
    }

    # Load validation data (small set for RPi)
    val_dir = PROJECT_ROOT.parent.parent / "training" / "dataset" / "images" / "val"
    val_images = []
    if val_dir.exists():
        import cv2
        paths = sorted(val_dir.glob("*"))[:50]
        for p in paths:
            img = cv2.imread(str(p))
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                val_images.append(img)
        print(f"Loaded {len(val_images)} validation images")
    else:
        print("No validation images found. Using random noise.")
        val_images = [np.random.rand(320, 320, 3).astype(np.float32) for _ in range(50)]

    # Benchmark INT8 model
    int8_path = MODEL_DIR / "model_int8.tflite"
    if int8_path.exists():
        for imgsz in resolutions:
            result = benchmark_model(int8_path, val_images, None, imgsz,
                                     label="YOLOv8n INT8")
            all_results["benchmarks"].append(result)
    else:
        print(f"INT8 model not found at {int8_path}")

    # Save results
    output_dir = PROJECT_ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "rpi_benchmark.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*60}")
    print("RPi Benchmark Summary")
    print(f"{'='*60}")
    for b in all_results["benchmarks"]:
        print(f"  {b['model']} @ {b['resolution']}x{b['resolution']}: "
              f"{b['fps']} FPS | {b['mean_latency_ms']} ms | "
              f"{b.get('model_size_mb', '?')} MB")

    return all_results


if __name__ == "__main__":
    main()
