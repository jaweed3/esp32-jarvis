#!/usr/bin/env python3
"""
Standalone evaluation with all 4 bug fixes applied.
Loads existing INT8 TFLite model and evaluates with correct:
  1. int8 dequantization (was uint8-only)
  2. int8 input quantization (was float-to-int8 crash)
  3. Coordinate scaling *imgsz (was missing)
  4. NMS post-processing (was missing)
"""

import json, time, sys, cv2, numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils

VAL_IMG_DIR = PROJECT_ROOT / "dataset" / "images" / "val"
VAL_LBL_DIR = PROJECT_ROOT / "dataset" / "labels" / "val"
TFLITE_PATH = PROJECT_ROOT / "quantized" / "yolov8n_int8.tflite"
IMSZ = 192
CONF_THRESH = 0.1
IOU_THRESH = 0.5


def load_val_data(imgsz, limit=200):
    img_paths = sorted(VAL_IMG_DIR.glob("*"))[:limit]
    lbl_paths = sorted(VAL_LBL_DIR.glob("*.txt"))[:limit]

    # Align by stem
    lbl_map = {p.stem: p for p in lbl_paths}
    images, labels = [], []
    for img_p in img_paths:
        if img_p.stem in lbl_map:
            img = cv2.imread(str(img_p))
            if img is None:
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (imgsz, imgsz))
            img = img.astype(np.float32) / 255.0
            images.append(img)
            labels.append(lbl_map[img_p.stem])

    print(f"  Loaded {len(images)} matched image-label pairs")
    return np.array(images), labels


def evaluate(tflite_path, val_images, val_labels, imgsz, conf_thresh=0.1, iou_thresh=0.5):
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    input_dtype = input_details["dtype"]
    input_quant = input_details.get("quantization", (1.0, 0))
    output_dtype = output_details["dtype"]
    output_quant = output_details.get("quantization", (0, 0))

    print(f"  Input dtype:  {input_dtype}, quant: {input_quant}")
    print(f"  Output dtype: {output_dtype}, quant: {output_quant}")

    # Bug #2 fix: proper input quantization for int8
    if input_dtype == np.uint8:
        calib_images = (val_images * 255).astype(np.uint8)
    elif input_dtype == np.int8:
        in_scale, in_zp = input_quant
        if in_scale is None or in_scale == 0:
            in_scale = 1.0
        if in_zp is None:
            in_zp = 0
        calib_images = np.clip(val_images / in_scale + in_zp, -128, 127).astype(np.int8)
    else:
        calib_images = val_images.astype(np.float32)

    predictions = []
    latencies = []

    for i in range(len(calib_images)):
        inp = calib_images[i:i+1]
        interpreter.set_tensor(input_details["index"], inp)
        start = time.perf_counter()
        interpreter.invoke()
        latencies.append((time.perf_counter() - start) * 1000)

        output = interpreter.get_tensor(output_details["index"])
        # Bug #1 fix: handle both uint8 AND int8
        if output_dtype in (np.uint8, np.int8):
            scale, zp = output_quant
            if scale is not None and zp is not None:
                output = (output.astype(np.float32) - zp) * scale

        boxes, scores, _ = utils.postprocess_yolo_output(output, conf_thresh, imgsz)
        predictions.append({
            "boxes": boxes.tolist() if len(boxes) else [],
            "scores": scores.tolist() if len(scores) else [],
        })

    # Ground truth (same as original — GT is in YOLO format [cx,cy,w,h] normalized)
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


def main():
    print("=" * 60)
    print("RescueVision Edge — Fixed TFLite Evaluation")
    print("=" * 60)

    if not TFLITE_PATH.exists():
        print(f"Model not found: {TFLITE_PATH}")
        return

    print(f"\nLoading validation data (imgsz={IMSZ})...")
    val_images, val_labels = load_val_data(IMSZ, limit=200)

    print(f"\nEvaluating: {TFLITE_PATH.name}")
    metrics = evaluate(TFLITE_PATH, val_images, val_labels, IMSZ, CONF_THRESH, IOU_THRESH)

    print(f"\n{'='*60}")
    print(f"RESULTS (with all 4 bug fixes)")
    print(f"{'='*60}")
    print(f"  mAP@0.5:     {metrics.get('mAP@0.5', 'N/A')}")
    print(f"  Precision:   {metrics.get('precision', 'N/A')}")
    print(f"  Recall:      {metrics.get('recall', 'N/A')}")
    print(f"  Latency:     {metrics.get('mean_latency_ms', 'N/A')} ms")
    print(f"  FPS:         {metrics.get('fps', 'N/A')}")
    print(f"{'='*60}")

    result_path = PROJECT_ROOT / "quantized" / "results_evaluation_fixed.json"
    with open(result_path, "w") as f:
        json.dump(metrics, f, indent=2, cls=utils.NumpyEncoder)
    print(f"Saved to {result_path}")


if __name__ == "__main__":
    main()
