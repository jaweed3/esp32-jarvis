#!/usr/bin/env python3
"""
03_quantize.py — Post-training quantization (PTQ) of YOLOv8n FP32 → INT8 via TFLite.

Steps:
1. Load trained FP32 ONNX model
2. Convert to TFLite with FP32 fallback
3. Apply INT8 quantization using representative dataset
4. Evaluate quantized model accuracy (mAP drop)
5. Profile quantized model size & latency
6. Save both TFLite variants to quantized/ directory
"""

import json
import time
from pathlib import Path

import numpy as np
import yaml
import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import DATASET_DIR, QUANTIZED_DIR, CONFIG_DIR

# Force TF logging off
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def representative_dataset_gen(calib_images, batch_size=1):
    """Generator for TFLite representative dataset (INT8 calibration)."""
    for img in calib_images:
        # img shape already (1, 192, 192, 3), dtype float32
        yield [img.astype(np.float32)]


def preprocess_for_tflite(image_paths, imgsz: int, limit: int = 200):
    """Load and preprocess images for calibration/evaluation."""
    import cv2
    images = []
    for path in image_paths[:limit]:
        img = cv2.imread(str(path))
        if img is None:
            continue
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (imgsz, imgsz))
        img = img.astype(np.float32) / 255.0
        images.append(img)
    return np.array(images)


def convert_to_tflite(onnx_path: Path, output_path: Path,
                      optimizations, representative_data=None):
    """Convert ONNX to TFLite with optional quantization."""
    import tensorflow as tf

    converter = tf.lite.TFLiteConverter.from_saved_model(str(onnx_path))

    # TF1 saved model → try ONNX-TF approach
    # Actually, we need onnx → tf saved model first
    # Use onnx-tf for conversion
    import onnx
    from onnx_tf.backend import prepare

    tf_rep = prepare(onnx.load(str(onnx_path)))
    tf_rep.export_graph(str(output_path.parent / "_tf_savedmodel"))

    converter = tf.lite.TFLiteConverter.from_saved_model(
        str(output_path.parent / "_tf_savedmodel")
    )
    converter.optimizations = optimizations

    if representative_data is not None:
        converter.representative_dataset = lambda: representative_data
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS_INT8
        ]
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8
    else:
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS
        ]

    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)

    return output_path


def evaluate_tflite(tflite_path: Path, val_images: np.ndarray,
                    val_labels: list, imgsz: int, conf_thresh: float = 0.25,
                    iou_thresh: float = 0.5) -> dict:
    """Run inference with TFLite model and compute mAP."""
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    input_dtype = input_details[0]["dtype"]
    input_scale, input_zero_point = input_details[0]["quantization"] \
        if input_details[0]["quantization"] != (0.0, 0) else (1.0, 0)

    # Preprocess images to match input dtype
    if input_dtype == np.uint8:
        calib_images = (val_images * 255).astype(np.uint8)
    else:
        calib_images = val_images.astype(np.float32)

    predictions = []
    latencies = []

    for i in tqdm.trange(len(calib_images), desc="Evaluating TFLite"):
        inp = calib_images[i:i+1]
        interpreter.set_tensor(input_details[0]["index"], inp)

        start = time.perf_counter()
        interpreter.invoke()
        elapsed = time.perf_counter() - start
        latencies.append(elapsed * 1000)

        output = interpreter.get_tensor(output_details[0]["index"])
        # Post-process YOLO output (simplified)
        boxes, scores, _ = postprocess_yolo_output(output, conf_thresh, imgsz)
        predictions.append({
            "boxes": boxes.tolist() if len(boxes) else [],
            "scores": scores.tolist() if len(scores) else [],
        })

    # Build ground truth (from label files)
    # For benchmarking, we use synthetic labels
    gt = []
    for lbl in val_labels:
        with open(lbl) as f:
            lines = f.read().strip().split("\n")
        boxes = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) == 5:
                _, cx, cy, w, h = map(float, parts)
                x1 = (cx - w / 2) * imgsz
                y1 = (cy - h / 2) * imgsz
                x2 = (cx + w / 2) * imgsz
                y2 = (cy + h / 2) * imgsz
                boxes.append([x1, y1, x2, y2])
        gt.append({"boxes": boxes})

    metrics = utils.compute_map(predictions, gt, iou_thresh, conf_thresh)
    metrics["mean_latency_ms"] = round(float(np.mean(latencies)), 2)
    metrics["fps"] = round(1000 / metrics["mean_latency_ms"], 1)

    return metrics


def postprocess_yolo_output(output, conf_thresh, imgsz):
    """Minimal YOLO output post-processing (single-class)."""
    # YOLOv8n outputs (1, 84, 8400) → [cx, cy, w, h, class_scores...]
    output = np.squeeze(output)  # (84, 8400)
    if output.ndim == 2 and output.shape[0] == 84:
        boxes = output[:4, :]  # (4, 8400)
        scores = output[4:, :]  # (80, 8400)

        # For person class (index 0 in COCO after filtering)
        person_scores = np.max(scores[:1], axis=0)

        mask = person_scores > conf_thresh
        if not np.any(mask):
            return np.array([]), np.array([]), np.array([])

        boxes = boxes[:, mask]
        scores = person_scores[mask]

        # Convert [cx, cy, w, h] → [x1, y1, x2, y2]
        cx, cy, w, h = boxes
        x1 = (cx - w / 2) * imgsz
        y1 = (cy - h / 2) * imgsz
        x2 = (cx + w / 2) * imgsz
        y2 = (cy + h / 2) * imgsz
        boxes = np.stack([x1, y1, x2, y2], axis=1)

        return boxes, scores, np.zeros(len(scores))

    return np.array([]), np.array([]), np.array([])


def main():
    print("=" * 60)
    print("RescueVision Edge — Post-Training Quantization")
    print("=" * 60)

    cfg = utils.load_config()
    model_cfg = cfg["model"]
    quant_cfg = cfg["quantization"]
    imgsz = model_cfg["imgsz"]

    # Locate baseline ONNX model
    onnx_candidates = list(
        (PROJECT_ROOT / "baseline" / "yolov8n_fp32").glob("**/*.onnx")
    )
    if not onnx_candidates:
        print("No ONNX model found. Run 02_train_baseline.py first.")
        return

    onnx_path = onnx_candidates[0]
    print(f"Baseline ONNX: {onnx_path}")

    # Load representative images for INT8 calibration
    val_img_dir = DATASET_DIR / "images" / "val"
    val_img_paths = sorted(val_img_dir.glob("*"))[:quant_cfg["representative_dataset_size"]]
    print(f"Loading {len(val_img_paths)} calibration images...")

    calib_images = preprocess_for_tflite(
        val_img_paths, imgsz,
        limit=quant_cfg["representative_dataset_size"]
    )
    calib_gen = representative_dataset_gen(calib_images)

    # Load val labels for evaluation
    val_lbl_dir = DATASET_DIR / "labels" / "val"
    val_lbl_paths = sorted(val_lbl_dir.glob("*.txt"))[:200]

    # Convert 1: TFLite FP32 (no quantization)
    print("\n[1/2] Converting to TFLite FP32...")
    import tensorflow as tf
    tflite_fp32_path = QUANTIZED_DIR / "yolov8n_fp32.tflite"
    convert_to_tflite(
        onnx_path, tflite_fp32_path,
        optimizations=[tf.lite.Optimize.DEFAULT],
        representative_data=None,
    )
    size_fp32 = utils.profile_model_size(tflite_fp32_path)
    print(f"  TFLite FP32: {size_fp32['size_mb']} MB")

    # Convert 2: TFLite INT8 (quantized)
    print("\n[2/2] Converting to TFLite INT8 (quantized)...")
    tflite_int8_path = QUANTIZED_DIR / "yolov8n_int8.tflite"
    convert_to_tflite(
        onnx_path, tflite_int8_path,
        optimizations=[tf.lite.Optimize.DEFAULT],
        representative_data=calib_gen,
    )
    size_int8 = utils.profile_model_size(tflite_int8_path)
    print(f"  TFLite INT8: {size_int8['size_mb']} MB")

    # Evaluate both variants
    print("\nEvaluating TFLite FP32...")
    val_images = preprocess_for_tflite(val_img_paths, imgsz, limit=200)
    metrics_fp32 = evaluate_tflite(
        tflite_fp32_path, val_images, val_lbl_paths, imgsz
    )

    print("\nEvaluating TFLite INT8...")
    metrics_int8 = evaluate_tflite(
        tflite_int8_path, val_images, val_lbl_paths, imgsz
    )

    # Compile results
    results = {
        "model": "YOLOv8n",
        "input_size": imgsz,
        "variants": {
            "FP32 (baseline)": {
                "format": "PyTorch",
                "size_mb": utils.profile_model_size(
                    PROJECT_ROOT / "baseline" / "yolov8n_fp32" / "weights" / "best.pt"
                )["size_mb"],
            },
            "TFLite FP32": {
                "format": "TFLite Float32",
                "size_mb": size_fp32["size_mb"],
                **metrics_fp32,
            },
            "TFLite INT8": {
                "format": "TFLite Int8 Quantized",
                "size_mb": size_int8["size_mb"],
                **metrics_int8,
            },
        },
        "quantization_config": {
            "method": quant_cfg["method"],
            "target_dtype": quant_cfg["target_dtype"],
            "representative_dataset_size": quant_cfg["representative_dataset_size"],
        },
        "accuracy_drop_int8_vs_fp32": {
            "mAP_drop": round(
                metrics_fp32.get("mAP@0.5", 0) - metrics_int8.get("mAP@0.5", 0), 4
            ),
            "size_reduction_x": round(
                size_fp32["size_mb"] / max(size_int8["size_mb"], 0.1), 2
            ),
        },
    }

    utils.save_results(results, QUANTIZED_DIR, "quantization_comparison")

    print(f"\n{'='*60}")
    print(f"Quantization Results Summary")
    print(f"{'='*60}")
    for variant, data in results["variants"].items():
        print(f"  {variant}:")
        print(f"    Size: {data['size_mb']} MB")
        print(f"    mAP@0.5: {data.get('mAP@0.5', 'N/A')}")
        print(f"    Latency: {data.get('mean_latency_ms', 'N/A')} ms")
        print(f"    FPS: {data.get('fps', 'N/A')}")

    drop = results["accuracy_drop_int8_vs_fp32"]
    print(f"\n  INT8 vs FP32:")
    print(f"    mAP drop: {drop['mAP_drop']}")
    print(f"    Size reduction: {drop['size_reduction_x']}x")

    return results


if __name__ == "__main__":
    main()
