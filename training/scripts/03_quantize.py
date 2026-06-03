#!/usr/bin/env python3
"""
03_quantize.py — Post-training quantization (PTQ) of YOLOv8n FP32 → INT8 via TFLite.

Steps:
1. Load trained FP32 YOLO model
2. Export to TF SavedModel via Ultralytics
3. Convert to TFLite FP32 via TensorFlow
4. Apply INT8 quantization using representative dataset
5. Evaluate quantized model accuracy (mAP drop)
6. Profile quantized model size & latency
7. Save both TFLite variants to quantized/ directory
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

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def representative_dataset_gen(calib_images):
    for img in calib_images:
        yield [img[np.newaxis, ...].astype(np.float32)]


def preprocess_for_tflite(image_paths, imgsz: int, limit: int = 200):
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


def evaluate_tflite(tflite_path: Path, val_images: np.ndarray,
                    val_labels: list, imgsz: int, conf_thresh: float = 0.25,
                    iou_thresh: float = 0.5) -> dict:
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    input_dtype = input_details[0]["dtype"]
    calib_images = (val_images * 255).astype(np.uint8) if input_dtype == np.uint8 else val_images.astype(np.float32)

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
        boxes, scores, _ = utils.postprocess_yolo_output(output, conf_thresh, imgsz)
        predictions.append({
            "boxes": boxes.tolist() if len(boxes) else [],
            "scores": scores.tolist() if len(scores) else [],
        })

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


def convert_saved_model_to_tflite(saved_model_dir: Path, output_path: Path,
                                   representative_data=None,
                                   optimizations=None):
    import tensorflow as tf
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
    if representative_data is not None:
        converter.optimizations = optimizations or [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = lambda: representative_data
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8
    else:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(output_path), "wb") as f:
        f.write(tflite_model)
    print(f"  Saved TFLite model to {output_path}")


def main():
    print("=" * 60)
    print("RescueVision Edge — Post-Training Quantization")
    print("=" * 60)

    cfg = utils.load_config()
    model_cfg = cfg["model"]
    quant_cfg = cfg["quantization"]
    imgsz = model_cfg["imgsz"]

    pt_path = PROJECT_ROOT / "baseline" / "yolov8n_fp32" / "weights" / "best.pt"
    if not pt_path.exists():
        print(f"No trained model found at {pt_path}. Run 02_train_baseline.py first.")
        return

    print(f"Loading trained model: {pt_path}")

    from ultralytics import YOLO
    model = YOLO(str(pt_path))

    tf_savedmodel_dir = QUANTIZED_DIR / "_tf_savedmodel"
    if tf_savedmodel_dir.exists():
        import shutil
        shutil.rmtree(tf_savedmodel_dir)

    print("\nExporting to TF SavedModel...")
    model.export(format="saved_model", imgsz=imgsz, half=False, simplify=False)
    sm_export_path = PROJECT_ROOT / "baseline" / "yolov8n_fp32" / "weights" / "best_saved_model"
    if sm_export_path.exists():
        import shutil
        shutil.copytree(sm_export_path, tf_savedmodel_dir, dirs_exist_ok=True)

    val_img_dir = DATASET_DIR / "images" / "val"
    val_img_paths = sorted(val_img_dir.glob("*"))[:quant_cfg["representative_dataset_size"]]
    print(f"Loading {len(val_img_paths)} calibration images...")

    calib_images = preprocess_for_tflite(
        val_img_paths, imgsz,
        limit=quant_cfg["representative_dataset_size"]
    )
    calib_gen = representative_dataset_gen(calib_images)

    val_lbl_dir = DATASET_DIR / "labels" / "val"
    val_lbl_paths = sorted(val_lbl_dir.glob("*.txt"))[:200]

    print("\n[1/2] Converting to TFLite FP32...")
    tflite_fp32_path = QUANTIZED_DIR / "yolov8n_fp32.tflite"
    convert_saved_model_to_tflite(tf_savedmodel_dir, tflite_fp32_path, representative_data=None)
    size_fp32 = utils.profile_model_size(tflite_fp32_path)
    print(f"  TFLite FP32: {size_fp32['size_mb']} MB")

    print("\n[2/2] Converting to TFLite INT8 (quantized)...")
    tflite_int8_path = QUANTIZED_DIR / "yolov8n_int8.tflite"
    convert_saved_model_to_tflite(tf_savedmodel_dir, tflite_int8_path, representative_data=calib_gen)
    size_int8 = utils.profile_model_size(tflite_int8_path)
    print(f"  TFLite INT8: {size_int8['size_mb']} MB")

    print("\nEvaluating TFLite FP32...")
    val_images = preprocess_for_tflite(val_img_paths, imgsz, limit=200)
    metrics_fp32 = evaluate_tflite(tflite_fp32_path, val_images, val_lbl_paths, imgsz)

    print("\nEvaluating TFLite INT8...")
    metrics_int8 = evaluate_tflite(tflite_int8_path, val_images, val_lbl_paths, imgsz)

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
                "format": "TFLite Int8 Quantified",
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
