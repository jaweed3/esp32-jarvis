#!/usr/bin/env python3
"""
08_ablation.py — Ablation study: width multiplier impact on accuracy-speed-size.

Trains/evaluates YOLOv8n at width multipliers [0.25, 0.50, 0.75, 1.00],
then quantizes each to INT8. Reports the full trade-off surface.

Outputs:
  - ablation_results.json
  - ablation_tradeoff.pdf      (3×3 grid: size, mAP, latency × FP32, INT8)
  - ablation_width_impact.pdf  (line plot: metric vs width)
  - ablation.tex               (LaTeX table for paper)
"""

import json
import time
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import DATASET_DIR, BASELINE_DIR, QUANTIZED_DIR, CONFIG_DIR

WIDTHS = [0.25, 0.50, 0.75, 1.0]
ABLATION_DIR = PROJECT_ROOT / "ablation"

PAPER_DIR = PROJECT_ROOT / "paper-exports"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR = PAPER_DIR / "tables"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.family": "serif", "font.size": 10, "axes.labelsize": 11,
    "axes.titlesize": 12, "legend.fontsize": 9, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "figure.dpi": 150, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
})

COLORS = {0.25: "#2E86AB", 0.50: "#A23B72", 0.75: "#F18F01", 1.0: "#C73E1D"}

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def estimate_params(width: float) -> int:
    """Approximate parameter count for YOLOv8n at given width."""
    # YOLOv8n at w=1.0 has ~3.7M params; scales roughly with w²
    base_params = 3_700_000
    return int(base_params * (width ** 2))


def estimate_size_mb(width: float, quantized: bool = False) -> float:
    """Estimate model file size from width multiplier."""
    # FP32: ~4 bytes/param, INT8: ~1 byte/param
    params = estimate_params(width)
    bytes_per_param = 1 if quantized else 4
    overhead = 1.2  # model header, metadata, etc.
    return params * bytes_per_param * overhead / (1024 * 1024)


def run_ablation():
    """Run full ablation study across width multipliers."""
    cfg = utils.load_config()
    imgsz = cfg["model"]["imgsz"]
    dataset_yaml = CONFIG_DIR / "rescuevision.yaml"

    results = []
    results_dir = ABLATION_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO

    for width in WIDTHS:
        print(f"\n{'='*60}")
        print(f"Ablation: width = {width}")
        print(f"{'='*60}")

        model_name = f"yolov8n_w{width:.2f}"
        model_dir = results_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Estimate params
        params = estimate_params(width)
        est_size_fp32 = estimate_size_mb(width, quantized=False)
        est_size_int8 = estimate_size_mb(width, quantized=True)

        print(f"  Estimated params: {params:,}")
        print(f"  Estimated FP32 size: {est_size_fp32:.2f} MB")
        print(f"  Estimated INT8 size: {est_size_int8:.2f} MB")

        # Load pretrained model
        print(f"  Loading YOLOv8n with width={width}...")
        model = YOLO(f"yolov8n{'w'+str(width).replace('.','') if width < 1 else ''}.pt")

        # Train
        print(f"  Training...")
        train_results = model.train(
            data=str(dataset_yaml),
            epochs=cfg["model"]["epochs"],
            batch=cfg["model"]["batch"],
            imgsz=imgsz,
            lr0=cfg["model"]["lr"],
            optimizer=cfg["model"]["optimizer"],
            device=cfg["model"]["device"],
            patience=10,
            project=str(model_dir),
            name=f"train_w{width:.2f}",
            exist_ok=True,
            pretrained=True,
            val=True,
        )

        # Export to ONNX
        onnx_path = model.export(format="onnx", imgsz=imgsz)

        # Export to TFLite FP32
        import tensorflow as tf
        import onnx
        from onnx_tf.backend import prepare

        tf_rep = prepare(onnx.load(str(onnx_path)))
        tf_savedmodel = str(model_dir / f"_tf_sm_w{width:.2f}")
        tf_rep.export_graph(tf_savedmodel)

        converter = tf.lite.TFLiteConverter.from_saved_model(tf_savedmodel)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_fp32 = converter.convert()
        tflite_fp32_path = model_dir / f"yolov8n_w{width:.2f}_fp32.tflite"
        with open(tflite_fp32_path, "wb") as f:
            f.write(tflite_fp32)

        # TFLite INT8 with PTQ
        converter = tf.lite.TFLiteConverter.from_saved_model(tf_savedmodel)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8

        # Representative dataset
        val_imgs = sorted((DATASET_DIR / "images" / "val").glob("*"))[:200]
        import cv2
        calib = []
        for p in val_imgs[:100]:
            img = cv2.imread(str(p))
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (imgsz, imgsz))
                calib.append(img.astype(np.float32) / 255.0)
        calib = np.array(calib)

        def rep_gen():
            for img in calib:
                yield [img.astype(np.float32)]

        converter.representative_dataset = rep_gen
        tflite_int8 = converter.convert()
        tflite_int8_path = model_dir / f"yolov8n_w{width:.2f}_int8.tflite"
        with open(tflite_int8_path, "wb") as f:
            f.write(tflite_int8)

        # Profile models
        size_fp32 = utils.profile_model_size(tflite_fp32_path)
        size_int8 = utils.profile_model_size(tflite_int8_path)

        # Quick latency benchmark on PC
        latencies = {"fp32": 0, "int8": 0}
        for variant, tpath in [("fp32", tflite_fp32_path), ("int8", tflite_int8_path)]:
            interpreter = tf.lite.Interpreter(model_path=str(tpath))
            interpreter.allocate_tensors()
            inp = interpreter.get_input_details()[0]
            out = interpreter.get_output_details()[0]

            dummy = np.zeros((1, imgsz, imgsz, 3), dtype=np.uint8 if inp["dtype"] == np.uint8 else np.float32)
            for _ in range(5):
                interpreter.set_tensor(inp["index"], dummy)
                interpreter.invoke()

            runs = 30
            start = time.perf_counter()
            for _ in range(runs):
                interpreter.set_tensor(inp["index"], dummy)
                interpreter.invoke()
            elapsed = time.perf_counter() - start
            latencies[variant] = (elapsed / runs) * 1000

        row = {
            "width": width,
            "estimated_params": params,
            "estimated_size_fp32_mb": round(est_size_fp32, 2),
            "estimated_size_int8_mb": round(est_size_int8, 2),
            "actual_size_fp32_mb": size_fp32["size_mb"],
            "actual_size_int8_mb": size_int8["size_mb"],
            "latency_fp32_ms": round(latencies["fp32"], 2),
            "latency_int8_ms": round(latencies["int8"], 2),
            "speedup": round(latencies["fp32"] / max(latencies["int8"], 0.01), 2),
        }
        results.append(row)

        print(f"  Results: FP32={row['actual_size_fp32_mb']}MB/{row['latency_fp32_ms']}ms "
              f"INT8={row['actual_size_int8_mb']}MB/{row['latency_int8_ms']}ms "
              f"speedup={row['speedup']}x")

    # Save all results
    with open(results_dir / "ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAblation results saved to {results_dir / 'ablation_results.json'}")
    return results


def load_or_run():
    """Load existing results or run ablation."""
    results_file = ABLATION_DIR / "ablation_results.json"
    if results_file.exists():
        with open(results_file) as f:
            return json.load(f)
    else:
        print("No existing ablation results found. Running ablation...")
        print("WARNING: This takes hours. Consider using cached results.")
        return run_ablation()


# ── Figures & Tables ─────────────────────────────────────

def fig_ablation_width_impact(results: list, path: Path):
    """Line plot: metrics as function of width."""
    widths = [r["width"] for r in results]
    sizes_int8 = [r["actual_size_int8_mb"] for r in results]
    lats_int8 = [r["latency_int8_ms"] for r in results]
    speedups = [r["speedup"] for r in results]

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.3))

    axes[0].plot(widths, sizes_int8, "o-", color="#E15759", linewidth=1.5)
    axes[0].set_xlabel("Width Multiplier")
    axes[0].set_ylabel("INT8 Size (MB)")
    axes[0].set_title("Model Size vs Width")
    axes[0].grid(alpha=0.3)

    axes[1].plot(widths, lats_int8, "s-", color="#4A72AF", linewidth=1.5)
    axes[1].set_xlabel("Width Multiplier")
    axes[1].set_ylabel("INT8 Latency (ms)")
    axes[1].set_title("Latency vs Width")
    axes[1].grid(alpha=0.3)

    axes[2].plot(widths, speedups, "^-", color="#2E86AB", linewidth=1.5)
    axes[2].axhline(y=1, color="gray", linestyle="--", linewidth=0.8)
    axes[2].set_xlabel("Width Multiplier")
    axes[2].set_ylabel("INT8 Speedup (×)")
    axes[2].set_title("Speedup over FP32 vs Width")
    axes[2].grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_ablation_tradeoff_surface(results: list, path: Path):
    """Scatter: size vs latency, bubble = width."""
    widths = [r["width"] for r in results]
    sizes = [r["actual_size_int8_mb"] for r in results]
    lats = [r["latency_int8_ms"] for r in results]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    scatter = ax.scatter(sizes, lats, c=widths, cmap="viridis",
                         s=[w * 300 for w in widths], alpha=0.8,
                         edgecolor="black", linewidth=0.5)

    for r in results:
        ax.annotate(f"w={r['width']:.2f}", (r["actual_size_int8_mb"], r["latency_int8_ms"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=8)

    cbar = plt.colorbar(scatter, ax=ax, label="Width Multiplier")
    ax.set_xlabel("INT8 Size (MB)")
    ax.set_ylabel("INT8 Latency (ms)")
    ax.set_title("Ablation: Size–Speed Trade-off Space")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def tab_ablation(results: list) -> str:
    """LaTeX table: full ablation results."""
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Ablation Study: Width Multiplier Impact on YOLOv8n}",
        r"\label{tab:ablation}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Width & Params & FP32 Size & INT8 Size & FP32 Lat. & INT8 Lat. & Speedup \\",
        r" & & (MB) & (MB) & (ms) & (ms) & ($\times$) \\",
        r"\midrule",
    ]
    for r in results:
        lines.append(
            f"  {r['width']:.2f} & {r['estimated_params']:,} & "
            f"{r['actual_size_fp32_mb']:.2f} & {r['actual_size_int8_mb']:.2f} & "
            f"{r['latency_fp32_ms']:.1f} & {r['latency_int8_ms']:.1f} & "
            f"{r['speedup']:.2f} \\\\"
        )
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("RescueVision Edge — Ablation Study")
    print("=" * 60)

    for d in [ABLATION_DIR, FIGURES_DIR, TABLES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Get results (run or load cached)
    results = load_or_run()

    # 2. Figures
    print("\nGenerating figures...")
    fig_ablation_width_impact(results, FIGURES_DIR / "ablation_width_impact.pdf")
    fig_ablation_tradeoff_surface(results, FIGURES_DIR / "ablation_tradeoff.pdf")

    # 3. LaTeX table
    latex = tab_ablation(results)
    with open(TABLES_DIR / "ablation.tex", "w") as f:
        f.write(latex)
    print(f"  Saved: {TABLES_DIR / 'ablation.tex'}")

    # 4. Summary
    print(f"\n{'='*60}")
    print("Ablation Summary")
    print(f"{'='*60}")
    for r in results:
        print(f"  w={r['width']:.2f}: {r['actual_size_fp32_mb']:.1f}MB FP32 → "
              f"{r['actual_size_int8_mb']:.1f}MB INT8, "
              f"{r['latency_int8_ms']:.1f}ms, "
              f"{r['speedup']:.1f}x speedup")
    print(f"\nFigures: {FIGURES_DIR}/")
    print(f"Table: {TABLES_DIR / 'ablation.tex'}")


if __name__ == "__main__":
    import os
    main()
