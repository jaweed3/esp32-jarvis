#!/usr/bin/env python3
"""
02_train_baseline.py — Train/load YOLOv8n FP32 baseline on person detection dataset.

Steps:
1. Load ultralytics YOLOv8n (pretrained on COCO)
2. Fine-tune on RescueVision person dataset
3. Evaluate on validation set (mAP@0.5)
4. Profile model size, params, FLOPs, latency on PC
5. Export to ONNX FP32 and TorchScript
6. Save all results to baseline/ directory
"""

import json
import sys
import time
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils


def main():
    print("=" * 60)
    print("RescueVision Edge — FP32 Baseline Training")
    print("=" * 60)

    cfg = utils.load_config()
    model_cfg = cfg["model"]
    dataset_cfg = cfg["dataset"]

    # Dataset YAML
    dataset_yaml = PROJECT_ROOT / "configs" / "rescuevision.yaml"
    if not dataset_yaml.exists():
        print(f"Dataset YAML not found. Run 01_prepare_dataset.py first.")
        return

    # Load model
    print(f"\nLoading YOLOv8n (pretrained={model_cfg['pretrained']})...")
    model = YOLO("yolov8n.pt") if model_cfg["pretrained"] else YOLO("yolov8n.yaml")

    imgsz = model_cfg["imgsz"]

    # Train
    print(f"\nStarting training: imgsz={imgsz}, epochs={model_cfg['epochs']}, "
          f"batch={model_cfg['batch']}, lr={model_cfg['lr']}")
    results = model.train(
        data=str(dataset_yaml),
        epochs=model_cfg["epochs"],
        batch=model_cfg["batch"],
        imgsz=imgsz,
        lr0=model_cfg["lr"],
        optimizer=model_cfg["optimizer"],
        device=model_cfg["device"],
        patience=15,
        project=str(PROJECT_ROOT / "baseline"),
        name="yolov8n_fp32",
        exist_ok=True,
        pretrained=model_cfg["pretrained"],
        val=True,
        amp=True,
    )

    # Save best model
    best_pt = PROJECT_ROOT / "baseline" / "yolov8n_fp32" / "weights" / "best.pt"
    if not best_pt.exists():
        print(f"Warning: best.pt not found at {best_pt}")
        # Try alternate location
        alt = list((PROJECT_ROOT / "baseline" / "yolov8n_fp32" / "weights").glob("*.pt"))
        if alt:
            best_pt = alt[0]
        else:
            print("No trained weights found.")
            return

    # Export to ONNX FP32
    print(f"\nExporting to ONNX FP32...")
    onnx_path = model.export(format="onnx", imgsz=imgsz, half=False)
    print(f"ONNX model: {onnx_path}")

    # Export to TorchScript
    print(f"Exporting to TorchScript...")
    ts_path = model.export(format="torchscript", imgsz=imgsz)
    print(f"TorchScript model: {ts_path}")

    # Evaluate on validation set
    print(f"\nEvaluating on validation set...")
    val_results = model.val(
        data=str(dataset_yaml),
        imgsz=imgsz,
        batch=model_cfg["batch"],
        device=model_cfg["device"],
    )
    metrics = val_results.results_dict if hasattr(val_results, "results_dict") else {}

    # Profile model
    print(f"\nProfiling FP32 baseline...")
    size_info = utils.profile_model_size(best_pt)

    # Profile with torch
    torch_model = torch.jit.load(str(ts_path)) if Path(str(ts_path).replace(".pt", ".torchscript")).exists() else None

    profile = {
        "model": "YOLOv8n",
        "precision": "FP32",
        "input_size": imgsz,
        "weights_path": str(best_pt),
        "onnx_path": str(onnx_path),
        "torchscript_path": str(ts_path),
        **size_info,
        "metrics": metrics,
    }

    # Add FLOPs/latency if torch model available
    if torch_model:
        try:
            torch_profile = utils.profile_torch_model(
                torch_model, input_size=(1, 3, imgsz, imgsz)
            )
            profile.update(torch_profile)
        except Exception as e:
            print(f"Torch profiling failed: {e}")

    # Save results
    utils.save_results(profile, PROJECT_ROOT / "baseline", "fp32_baseline")

    print(f"\n--- FP32 Baseline Summary ---")
    print(f"  Model size: {profile['size_mb']} MB")
    print(f"  mAP@0.5: {profile.get('metrics', {}).get('metrics/mAP50(B)', 'N/A')}")
    print(f"  Params: {profile.get('total_params', 'N/A')}")
    print(f"  Latency: {profile.get('mean_latency_ms', 'N/A'):.2f} ms")
    print(f"  Results saved to: {PROJECT_ROOT / 'baseline'}")

    return profile


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
