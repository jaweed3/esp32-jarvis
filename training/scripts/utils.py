#!/usr/bin/env python3
"""
utils.py — Shared utilities for RescueVision Edge training pipeline.

Provides dataset loading, metric computation, model profiling, and
visualization helpers used across all experiment stages.
"""

import os
import json
import time
import yaml
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import torch
import torch.nn as nn
from ultralytics import YOLO
import cv2


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
BASELINE_DIR = PROJECT_ROOT / "baseline"
QUANTIZED_DIR = PROJECT_ROOT / "quantized"
CONFIG_DIR = PROJECT_ROOT / "configs"


def load_config(name: str = "experiment.yaml") -> dict:
    path = CONFIG_DIR / name
    with open(path) as f:
        return yaml.safe_load(f)


def load_yolo_model(weights_path: str | Path) -> YOLO:
    return YOLO(str(weights_path))


def profile_model_size(path: str | Path) -> dict:
    path = Path(path)
    size_bytes = path.stat().st_size
    return {
        "path": str(path),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "suffix": path.suffix,
    }


def profile_torch_model(model: nn.Module, input_size: Tuple[int, ...] = (1, 3, 640, 640)) -> dict:
    """Measure FLOPs, param count, and inference latency of a torch model."""
    device = next(model.parameters()).device
    dummy = torch.randn(*input_size).to(device)

    # Warmup
    for _ in range(10):
        _ = model(dummy)

    # Timed inference
    n_runs = 100
    torch.cuda.synchronize() if device.type == "cuda" else None
    start = time.perf_counter()
    for _ in range(n_runs):
        _ = model(dummy)
    torch.cuda.synchronize() if device.type == "cuda" else None
    elapsed = time.perf_counter() - start

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    return {
        "total_params": total_params,
        "trainable_params": trainable_params,
        "mean_latency_ms": (elapsed / n_runs) * 1000,
        "fps": n_runs / elapsed,
        "input_size": input_size,
    }


def compute_map(predictions: List[Dict], ground_truths: List[Dict],
                iou_thresh: float = 0.5, conf_thresh: float = 0.25) -> Dict:
    """
    Simplified mAP computation.
    predictions: list of {boxes, scores, labels} per image
    ground_truths: list of {boxes, labels} per image
    """
    from sklearn.metrics import auc

    n_gt = sum(len(g["boxes"]) for g in ground_truths)
    if n_gt == 0:
        return {"mAP@0.5": 0.0, "precision": 0.0, "recall": 0.0}

    all_tp_fp = []

    for pred, gt in zip(predictions, ground_truths):
        if len(pred["boxes"]) == 0:
            continue

        gt_boxes = np.array(gt["boxes"])
        pred_boxes = np.array(pred["boxes"])
        pred_scores = np.array(pred["scores"])

        order = np.argsort(-pred_scores)
        pred_boxes = pred_boxes[order]
        pred_scores = pred_scores[order]

        tp = np.zeros(len(pred_boxes))
        fp = np.zeros(len(pred_boxes))
        matched_gts = set()

        for i, pb in enumerate(pred_boxes):
            ious = [bbox_iou(pb, gb) for gb in gt_boxes]
            best_idx = np.argmax(ious) if ious else -1
            best_iou = max(ious) if ious else 0

            if best_iou >= iou_thresh and best_idx not in matched_gts:
                tp[i] = 1
                matched_gts.add(best_idx)
            else:
                fp[i] = 1

        for t, f in zip(tp, fp):
            all_tp_fp.append((t, f, n_gt))

    if not all_tp_fp:
        return {"mAP@0.5": 0.0, "precision": 0.0, "recall": 0.0}

    tp_cum = np.cumsum([x[0] for x in all_tp_fp])
    fp_cum = np.cumsum([x[1] for x in all_tp_fp])
    precisions = tp_cum / (tp_cum + fp_cum + 1e-8)
    recalls = tp_cum / n_gt

    ap = 0
    for t in np.linspace(0, 1, 11):
        p = max([p for p, r in zip(precisions, recalls) if r >= t], default=0)
        ap += p / 11

    return {
        "mAP@0.5": round(ap, 4),
        "precision": round(float(np.mean(precisions)), 4),
        "recall": round(float(np.mean(recalls)), 4),
    }


def bbox_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter + 1e-8
    return inter / union


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def save_results(results: dict, path: Path, label: str = "") -> None:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    fname = f"results_{label}.json" if label else "results.json"
    with open(path / fname, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"Results saved to {path / fname}")


def load_results(path: Path, label: str = "") -> dict:
    fname = f"results_{label}.json" if label else "results.json"
    with open(Path(path) / fname) as f:
        return json.load(f)


def letterbox_imgsz(model: YOLO) -> int:
    """Extract model preferred input size from YOLO metadata."""
    try:
        return model.model.args.get("imgsz", 640) if hasattr(model, "model") else 640
    except Exception:
        return 640


def postprocess_yolo_output(output, conf_thresh, imgsz):
    """Minimal YOLO output post-processing (single-class person detection).
    Handles both (84, N) multi-class and (5, N) single-class formats."""
    output = np.squeeze(output)
    if output.ndim != 2:
        return np.array([]), np.array([]), np.array([])

    n_dims, n_boxes = output.shape

    if n_dims == 84:
        boxes = output[:4, :]
        scores = output[4:, :]
        person_scores = np.max(scores[:1], axis=0)
    elif n_dims == 5:
        boxes = output[:4, :]
        person_scores = output[4, :]
    else:
        return np.array([]), np.array([]), np.array([])

    mask = person_scores > conf_thresh
    if not np.any(mask):
        return np.array([]), np.array([]), np.array([])

    boxes = boxes[:, mask]
    scores = person_scores[mask]

    cx, cy, w, h = boxes
    x1 = (cx - w / 2) * imgsz
    y1 = (cy - h / 2) * imgsz
    x2 = (cx + w / 2) * imgsz
    y2 = (cy + h / 2) * imgsz
    boxes = np.stack([x1, y1, x2, y2], axis=1)

    return boxes, scores, np.zeros(len(scores))


def class_labels_for_sar() -> List[str]:
    """Return class labels relevant to SAR victim detection."""
    return ["person"]
