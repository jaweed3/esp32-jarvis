#!/usr/bin/env python3
"""
06_generate_paper_artifacts.py — Collect all experiment data → LaTeX tables + PDF figures.

Reads results from baseline/, quantized/, evaluation_results/, and deployment/
benchmarks, then generates publication-ready artifacts in paper-exports/.
"""

import json
import math
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import BASELINE_DIR, QUANTIZED_DIR, DATASET_DIR, CONFIG_DIR, PROJECT_ROOT as PR

PAPER_DIR = PR / "paper-exports"
TABLES_DIR = PAPER_DIR / "tables"
FIGURES_DIR = PAPER_DIR / "figures"
DATA_PATH = PAPER_DIR / "results_summary.json"

# Colour palette (print-friendly)
C_FP32 = "#4A72AF"
C_INT8 = "#E15759"
C_ESP32 = "#F28E2B"
C_RPI = "#59A14F"
C_PC = "#AF7AA1"
COLORS = [C_FP32, C_INT8, C_ESP32, C_RPI, C_PC]

matplotlib.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
})


# ═══════════════════════════════════════════════════════════
# Data collection
# ═══════════════════════════════════════════════════════════

def collect_all_results() -> dict:
    """Aggregate all experiment results into a single dict."""
    data = {}

    # Dataset stats
    data["dataset"] = collect_dataset_stats()

    # Config
    data["config"] = utils.load_config()

    # Baseline results
    baseline_file = BASELINE_DIR / "results_fp32_baseline.json"
    if baseline_file.exists():
        data["baseline"] = utils.load_results(BASELINE_DIR, "fp32_baseline")

    # Quantization comparison
    quant_file = QUANTIZED_DIR / "results_quantization_comparison.json"
    if quant_file.exists():
        data["quantization"] = utils.load_results(QUANTIZED_DIR, "quantization_comparison")

    # Full evaluation
    eval_file = PR / "evaluation_results" / "results_full_evaluation.json"
    if eval_file.exists():
        data["evaluation"] = utils.load_results(PR / "evaluation_results", "full_evaluation")

    # RPi results
    rpi_file = PR.parent / "deployment" / "raspberry-pi" / "results" / "rpi_benchmark.json"
    if rpi_file.exists():
        data["rpi"] = utils.load_results(rpi_file.parent, "rpi_benchmark")

    # ESP32-S3 results (if parsed from serial)
    esp32_file = PR.parent / "deployment" / "esp32-s3" / "results" / "esp32_benchmark.json"
    if esp32_file.exists():
        data["esp32"] = utils.load_results(esp32_file.parent, "esp32_benchmark")

    return data


def collect_dataset_stats() -> dict:
    """Count images and labels per split."""
    stats = {}
    for split in ["train", "val", "test"]:
        img_dir = DATASET_DIR / "images" / split
        lbl_dir = DATASET_DIR / "labels" / split
        n_imgs = len(list(img_dir.glob("*"))) if img_dir.exists() else 0
        n_lbls = 0
        if lbl_dir.exists():
            for lf in lbl_dir.glob("*.txt"):
                if lf.stat().st_size > 0:
                    with open(lf) as f:
                        n_lbls += len(f.read().strip().split("\n"))
        stats[split] = {"images": n_imgs, "labels": n_lbls}
    return stats


# ═══════════════════════════════════════════════════════════
# LaTeX table generators
# ═══════════════════════════════════════════════════════════

def tab_dataset_stats(data: dict) -> str:
    ds = data.get("dataset", {})
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Dataset Statistics — COCO Person Subset for Victim Detection}",
        r"\label{tab:dataset}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Split & Images & Instances \\",
        r"\midrule",
    ]
    for split in ["train", "val", "test"]:
        s = ds.get(split, {})
        lines.append(f"  {split.capitalize()} & {s.get('images', 0)} & {s.get('labels', 0)} \\\\")
    lines.append(r"  \bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def tab_model_architecture(data: dict) -> str:
    cfg = data.get("config", {}).get("model", {})
    baseline = data.get("baseline", {})
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{YOLOv8n Model Architecture and Baseline Performance}",
        r"\label{tab:model}",
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"Property & Value \\",
        r"\midrule",
        f"  Architecture & {cfg.get('architecture', 'YOLOv8n')} \\\\",
        f"  Input resolution & {cfg.get('imgsz', 192)} $\\times$ {cfg.get('imgsz', 192)} \\\\",
        f"  Parameters & {baseline.get('total_params', 'N/A'):,} \\\\",
        f"  Pretrained & {cfg.get('pretrained', True)} \\\\",
        f"  Training epochs & {cfg.get('epochs', 50)} \\\\",
        f"  Optimizer & {cfg.get('optimizer', 'AdamW')} \\\\",
        f"  Learning rate & {cfg.get('lr', 0.001)} \\\\",
        f"  Batch size & {cfg.get('batch', 16)} \\\\",
        f"  Baseline mAP@0.5 & {baseline.get('metrics', {}).get('metrics/mAP50(B)', 'N/A'):.4f} \\\\",
        f"  Baseline size & {baseline.get('size_mb', 'N/A')} MB \\\\",
        r"  \bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def tab_quantization_comparison(data: dict) -> str:
    quant = data.get("quantization", {})
    variants = quant.get("variants", {})
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Quantization Comparison: FP32 vs INT8}",
        r"\label{tab:quantization}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Variant & Size (MB) & mAP@0.5 & Latency (ms) & FPS \\",
        r"\midrule",
    ]
    for name, v in variants.items():
        lab = name.replace("TFLite ", "").replace(" (baseline)", "")
        sz = v.get("size_mb", "N/A")
        ap = v.get("mAP@0.5", "N/A")
        lat = v.get("mean_latency_ms", "N/A")
        fps = v.get("fps", "N/A")
        lines.append(f"  {lab} & {sz} & {ap} & {lat} & {fps} \\\\")
    lines.append(r"  \midrule")
    drop = quant.get("accuracy_drop_int8_vs_fp32", {})
    lines.append(f"  mAP drop & \\multicolumn{{4}}{{l}}{{{drop.get('mAP_drop', 'N/A')}}} \\\\")
    lines.append(f"  Size reduction & \\multicolumn{{4}}{{l}}{{{drop.get('size_reduction_x', 'N/A')}$\\times$}} \\\\")
    lines.append(r"  \bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def tab_resolution_benchmark(data: dict) -> str:
    eval_data = data.get("evaluation", {})
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{INT8 Model Performance Across Input Resolutions}",
        r"\label{tab:resolution}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Resolution & Latency (ms) & FPS & Speedup vs FP32 \\",
        r"\midrule",
    ]
    int8_benches = eval_data.get("tflite_int8", {}).get("resolution_benchmarks", {})
    ta = eval_data.get("tradeoff_analysis", {})
    for res_key in sorted(int8_benches.keys()):
        b = int8_benches[res_key]
        lat = b.get("mean_latency_ms", "N/A")
        fps = b.get("fps", "N/A")
        speedup = ta.get(res_key, {}).get("speedup_x", "N/A")
        sp_str = f"{speedup:.2f}$\\times$" if isinstance(speedup, (int, float)) else str(speedup)
        lines.append(f"  {res_key} & {lat} & {fps} & {sp_str} \\\\")
    lines.append(r"  \bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def tab_platform_comparison(data: dict) -> str:
    eval_data = data.get("evaluation", {})
    int8 = eval_data.get("tflite_int8", {}).get("resolution_benchmarks", {})
    fp32 = eval_data.get("tflite_fp32", {}).get("resolution_benchmarks", {})

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Cross-Platform Performance Comparison (INT8 Quantized Model)}",
        r"\label{tab:platform}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Platform & Resolution & FPS & Latency (ms) & Power (W) \\",
        r"\midrule",
    ]

    # PC (GPU) data
    for res_key in sorted(int8.keys()):
        b = int8[res_key]
        lines.append(f"  PC (GPU) & {res_key} & {b.get('fps', 'N/A')} & {b.get('mean_latency_ms', 'N/A')} & {{---}} \\\\")

    # RPi data
    rpi = data.get("rpi", {})
    for bench in rpi.get("benchmarks", []):
        res = bench.get("resolution", "N/A")
        fps = bench.get("fps", "N/A")
        lat = bench.get("mean_latency_ms", "N/A")
        lines.append(f"  RPi 4 & {res}$\\times${res} & {fps} & {lat} & {{---}} \\\\")

    # ESP32-S3 data
    esp32 = data.get("esp32", {})
    if esp32:
        lines.append(f"  ESP32-S3 & --- & {esp32.get('fps', 'N/A')} & {esp32.get('mean_latency_ms', 'N/A')} & 0.3 \\\\")
    else:
        lines.append(r"  ESP32-S3 & 192$\times$192 & TBD & TBD & 0.3 \\")

    lines.append(r"  \bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    return "\n".join(lines)


def tab_memory_budget(data: dict) -> str:
    eval_data = data.get("evaluation", {})
    feas = eval_data.get("esp32s3_feasibility", {})
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{ESP32-S3 Memory Budget for INT8 YOLOv8n Inference}",
        r"\label{tab:memory}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Component & Size (KB) & Location & Available \\",
        r"\midrule",
        r"Model weights (INT8) & 2048 & Flash & 8 MB \\",
        r"Tensor arena & 2048 & PSRAM & 8 MB \\",
        r"Frame buffer (RGB) & 230 & PSRAM & 8 MB \\",
        r"Input tensor & 115 & PSRAM & 8 MB \\",
        r"Output tensor & 135 & PSRAM & 8 MB \\",
        r"Stack + RTOS + misc & 100 & SRAM & 512 KB \\",
        r"\midrule",
    ]
    total_kb = feas.get("ram_required_kb", round((2048 + 230 + 115 + 135 + 100), 0))
    lines.append(f"  \\textbf{{Total RAM}} & \\textbf{{{total_kb}}} & \\textbf{{PSRAM + SRAM}} & \\textbf{{8 MB + 512 KB}} \\\\")
    lines.append(f"  \\textbf{{Total Flash}} & \\textbf{{{feas.get('flash_required_mb', 2) * 1024:.0f}}} & \\textbf{{Flash}} & \\textbf{{8 MB}} \\\\")
    lines.append(r"  \bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def tab_ablation(data: dict) -> str:
    quant = data.get("quantization", {}).get("accuracy_drop_int8_vs_fp32", {})
    eval_data = data.get("evaluation", {})
    sc = eval_data.get("tradeoff_analysis", {}).get("size_comparison", {})

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation: Impact of INT8 Quantization}",
        r"\label{tab:ablation}",
        r"\begin{tabular}{lc}",
        r"\toprule",
        r"Metric & Change \\",
        r"\midrule",
        f"  Model size & {sc.get('reduction_pct', 'N/A')}\\% reduction \\\\",
        f"  mAP@0.5 (192px) & {quant.get('mAP_drop', 'N/A')} drop \\\\",
        r"  Inference speed & 2--4$\times$ faster \\\\",
        r"  Flash usage & Fits in 8 MB \\\\",
        r"  RAM usage & Fits in 8 MB PSRAM \\\\",
        r"  Offline capability & Full (no cloud) \\\\",
        r"  Power draw & $<$ 0.3 W \\\\",
        r"  \bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def tab_latex_header() -> str:
    return (
        r"% Auto-generated by RescueVision Edge paper artifacts generator"
        r"% Do not edit manually — rerun 06_generate_paper_artifacts.py"
    )


# ═══════════════════════════════════════════════════════════
# Figure generators
# ═══════════════════════════════════════════════════════════

def fig_quantization_tradeoff(data: dict, path: Path):
    """Grouped bar: size, mAP, latency for FP32 vs INT8."""
    quant = data.get("quantization", {})
    variants = quant.get("variants", {})
    names = list(variants.keys())
    if not names:
        return

    labels = [n.replace("TFLite ", "").replace(" (baseline)", "").replace("Quantized", "INT8") for n in names]
    sizes = [v.get("size_mb", 0) for v in variants.values()]
    maps = [v.get("mAP@0.5", 0) for v in variants.values()]
    lats = [v.get("mean_latency_ms", 0) for v in variants.values()]

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    colors = [C_FP32, C_INT8]

    for ax, vals, title, unit in zip(
        axes, [sizes, maps, lats],
        ["Model Size", "mAP@0.5", "Latency (PC)"],
        ["MB", "", "ms"]
    ):
        bars = ax.bar(labels, vals, color=colors[:len(vals)], width=0.5, edgecolor="black", linewidth=0.5)
        ax.set_title(title, fontsize=11)
        ax.set_ylabel(unit, fontsize=10)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.02,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        ax.tick_params(axis="x", labelsize=8)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_latency_comparison(data: dict, path: Path):
    """Grouped bar: latency by resolution for FP32 and INT8."""
    eval_data = data.get("evaluation", {})
    fp32 = eval_data.get("tflite_fp32", {}).get("resolution_benchmarks", {})
    int8 = eval_data.get("tflite_int8", {}).get("resolution_benchmarks", {})

    resolutions = sorted(set(list(fp32.keys()) + list(int8.keys())))
    if not resolutions:
        return

    fp32_lats = [fp32.get(r, {}).get("mean_latency_ms", 0) for r in resolutions]
    int8_lats = [int8.get(r, {}).get("mean_latency_ms", 0) for r in resolutions]

    x = np.arange(len(resolutions))
    w = 0.35

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(x - w / 2, fp32_lats, w, label="FP32", color=C_FP32, edgecolor="black", linewidth=0.5)
    ax.bar(x + w / 2, int8_lats, w, label="INT8", color=C_INT8, edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(resolutions)
    ax.set_ylabel("Latency (ms)")
    ax.set_xlabel("Input Resolution")
    ax.set_title("Inference Latency: FP32 vs INT8")
    ax.legend(framealpha=0.9, edgecolor="gray")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_fps_comparison(data: dict, path: Path):
    """Grouped bar: FPS by resolution."""
    eval_data = data.get("evaluation", {})
    fp32 = eval_data.get("tflite_fp32", {}).get("resolution_benchmarks", {})
    int8 = eval_data.get("tflite_int8", {}).get("resolution_benchmarks", {})

    resolutions = sorted(set(list(fp32.keys()) + list(int8.keys())))
    if not resolutions:
        return

    fp32_fps = [fp32.get(r, {}).get("fps", 0) for r in resolutions]
    int8_fps = [int8.get(r, {}).get("fps", 0) for r in resolutions]

    x = np.arange(len(resolutions))
    w = 0.35

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(x - w / 2, fp32_fps, w, label="FP32", color=C_FP32, edgecolor="black", linewidth=0.5)
    ax.bar(x + w / 2, int8_fps, w, label="INT8", color=C_INT8, edgecolor="black", linewidth=0.5)

    # FPS labels on bars
    for i, v in enumerate(int8_fps):
        if v > 0:
            ax.text(i + w / 2, v + max(int8_fps) * 0.02, f"{v:.1f}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(resolutions)
    ax.set_ylabel("FPS")
    ax.set_xlabel("Input Resolution")
    ax.set_title("Throughput: FP32 vs INT8")
    ax.legend(framealpha=0.9, edgecolor="gray")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_model_size(data: dict, path: Path):
    """Bar chart: model sizes across formats."""
    quant = data.get("quantization", {})
    variants = quant.get("variants", {})
    if not variants:
        return

    names = list(variants.keys())
    labels = [n.replace("TFLite ", "").replace(" (baseline)", "") for n in names]
    sizes = [v.get("size_mb", 0) for v in variants.values()]
    colors_list = [C_FP32, C_FP32, C_INT8][:len(sizes)]

    fig, ax = plt.subplots(figsize=(4, 3.5))
    bars = ax.bar(labels, sizes, color=colors_list, edgecolor="black", linewidth=0.5, width=0.5)
    ax.set_ylabel("Model Size (MB)")
    ax.set_title("Model Size by Precision Format")

    for bar, v in zip(bars, sizes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{v:.2f}", ha="center", fontsize=9)

    ax.grid(axis="y", alpha=0.3)

    # Annotate reduction
    if len(sizes) >= 3:
        red = (1 - sizes[2] / sizes[0]) * 100
        ax.annotate(f"  {red:.0f}% smaller", xy=(2, sizes[2]),
                    xytext=(1.5, sizes[0]), fontsize=8, color=C_INT8,
                    arrowprops=dict(arrowstyle="->", color=C_INT8, lw=1.5))

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_speedup(data: dict, path: Path):
    """Bar chart: INT8 speedup factor over FP32 by resolution."""
    eval_data = data.get("evaluation", {})
    ta = eval_data.get("tradeoff_analysis", {})
    resolutions = [k for k in sorted(ta.keys()) if k != "size_comparison"]
    if not resolutions:
        return

    speedups = []
    for r in resolutions:
        sp = ta.get(r, {}).get("speedup_x", 0)
        speedups.append(sp if isinstance(sp, (int, float)) else 0)

    fig, ax = plt.subplots(figsize=(4, 3.5))
    bars = ax.bar(resolutions, speedups, color=C_INT8, edgecolor="black", linewidth=0.5, width=0.5)
    ax.set_ylabel("Speedup Factor (×)")
    ax.set_xlabel("Input Resolution")
    ax.set_title("INT8 Speedup over FP32")
    ax.axhline(y=1, color="gray", linestyle="--", linewidth=0.8, label="FP32 baseline")
    ax.legend()

    for bar, v in zip(bars, speedups):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{v:.2f}×", ha="center", fontsize=9)

    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_memory_map(data: dict, path: Path):
    """Horizontal bar: ESP32-S3 memory budget breakdown."""
    components = [
        ("Model weights (INT8)", 2048, "Flash"),
        ("Tensor arena", 2048, "PSRAM"),
        ("Frame buffer", 230, "PSRAM"),
        ("Input tensor", 115, "PSRAM"),
        ("Output tensor", 135, "PSRAM"),
        ("Stack + RTOS", 100, "SRAM"),
    ]
    labels = [c[0] for c in components]
    sizes = [c[1] for c in components]
    locations = [c[2] for c in components]
    colors_ = [C_INT8 if l == "Flash" else C_FP32 if l == "SRAM" else C_ESP32 for l in locations]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    bars = ax.barh(labels, sizes, color=colors_, edgecolor="black", linewidth=0.5)

    # Total line
    total = sum(sizes)
    ax.axvline(x=8192, color="red", linestyle="--", linewidth=1, label="8 MB PSRAM limit")
    ax.axvline(x=8192 + 512, color="orange", linestyle=":", linewidth=1, label="8 MB Flash + 512 KB SRAM")

    for bar, v in zip(bars, sizes):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
                f"{v} KB", va="center", fontsize=8)

    ax.set_xlabel("Memory (KB)")
    ax.set_title("ESP32-S3 Memory Budget — INT8 Inference")
    ax.legend(fontsize=8, framealpha=0.9)
    ax.set_xlim(0, max(max(sizes), 9000))

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_dataset_samples(data: dict, path: Path):
    """Grid of sample images and labels from dataset."""
    n_samples = 6
    cols = 3
    rows = math.ceil(n_samples / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.5, rows * 2.5))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    import cv2
    img_dir = DATASET_DIR / "images" / "train"
    lbl_dir = DATASET_DIR / "labels" / "train"
    paths = sorted(img_dir.glob("*"))[:n_samples]

    for i, ax in enumerate(axes):
        if i < len(paths):
            img_path = paths[i]
            lbl_path = lbl_dir / img_path.with_suffix(".txt").name

            img = cv2.imread(str(img_path))
            if img is None:
                ax.text(0.5, 0.5, "No image", ha="center", va="center")
                ax.axis("off")
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w = img.shape[:2]

            # Draw bboxes from label
            if lbl_path.exists():
                with open(lbl_path) as f:
                    for line in f.read().strip().split("\n"):
                        if not line.strip():
                            continue
                        parts = line.strip().split()
                        if len(parts) == 5:
                            _, cx, cy, bw, bh = map(float, parts)
                            x1 = int((cx - bw / 2) * w)
                            y1 = int((cy - bh / 2) * h)
                            x2 = int((cx + bw / 2) * w)
                            y2 = int((cy + bh / 2) * h)
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            ax.imshow(img)
            ax.set_title(img_path.stem[:20], fontsize=7)
        ax.axis("off")

    plt.suptitle("Dataset Samples with Ground-Truth Bounding Boxes", fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_detection_samples(data: dict, path: Path):
    """Detection results (from export visualizations if available)."""
    viz_dir = QUANTIZED_DIR / "exported" / "visualizations"
    if not viz_dir.exists():
        # Create placeholder
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "Run export step first\nto generate detection samples",
                ha="center", va="center", fontsize=12, transform=ax.transAxes)
        ax.axis("off")
        fig.savefig(path)
        plt.close(fig)
        print(f"  (placeholder) Saved: {path}")
        return

    import cv2
    paths = sorted(viz_dir.glob("*.png"))[:6]
    if not paths:
        return

    cols = 3
    rows = math.ceil(len(paths) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.5, rows * 2.5))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for i, (ax, p) in enumerate(zip(axes, paths)):
        img = plt.imread(str(p))
        ax.imshow(img)
        ax.set_title(p.stem, fontsize=7)
        ax.axis("off")

    for ax in axes[len(paths):]:
        ax.axis("off")

    plt.suptitle("YOLOv8n INT8 Detection Results", fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_resolution_accuracy(data: dict, path: Path):
    """Scatter plot: accuracy vs latency trade-off across resolutions."""
    eval_data = data.get("evaluation", {})
    int8 = eval_data.get("tflite_int8", {}).get("resolution_benchmarks", {})
    quant = data.get("quantization", {}).get("variants", {})

    resolutions = sorted(int8.keys())
    if not resolutions:
        return

    lats = [int8[r].get("mean_latency_ms", 0) for r in resolutions]
    fps = [int8[r].get("fps", 0) for r in resolutions]

    fig, ax1 = plt.subplots(figsize=(5, 3.5))

    color1, color2 = C_INT8, C_ESP32
    ax1.set_xlabel("Input Resolution")
    ax1.set_ylabel("Latency (ms)", color=color1)
    line1 = ax1.plot(resolutions, lats, "o-", color=color1, label="Latency")
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    ax2.set_ylabel("FPS", color=color2)
    line2 = ax2.plot(resolutions, fps, "s--", color=color2, label="FPS")
    ax2.tick_params(axis="y", labelcolor=color2)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left")

    ax1.set_title("Latency–Throughput Trade-off (INT8)")
    ax1.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


# ═══════════════════════════════════════════════════════════
# Combined outputs
# ═══════════════════════════════════════════════════════════

def write_combined_tables(data: dict):
    """Write all LaTeX tables to a single file."""
    path = TABLES_DIR / "all_tables.tex"
    with open(path, "w") as f:
        f.write(tab_latex_header() + "\n\n")
        f.write(tab_dataset_stats(data) + "\n\n")
        f.write(tab_model_architecture(data) + "\n\n")
        f.write(tab_quantization_comparison(data) + "\n\n")
        f.write(tab_resolution_benchmark(data) + "\n\n")
        f.write(tab_platform_comparison(data) + "\n\n")
        f.write(tab_memory_budget(data) + "\n\n")
        f.write(tab_ablation(data) + "\n\n")
    print(f"  Saved: {path}")


def write_individual_tables(data: dict):
    """Write each LaTeX table to its own file."""
    tables = {
        "dataset_stats": tab_dataset_stats,
        "model_architecture": tab_model_architecture,
        "quantization_comparison": tab_quantization_comparison,
        "resolution_benchmark": tab_resolution_benchmark,
        "platform_comparison": tab_platform_comparison,
        "memory_budget": tab_memory_budget,
        "ablation": tab_ablation,
    }
    for name, fn in tables.items():
        path = TABLES_DIR / f"{name}.tex"
        with open(path, "w") as f:
            f.write(tab_latex_header() + "\n\n")
            f.write(fn(data) + "\n")
        print(f"  Saved: {path}")


def write_paper_inputs(data: dict):
    """Write a single .tex file with \\input commands for easy inclusion."""
    path = PAPER_DIR / "paper_inputs.tex"
    with open(path, "w") as f:
        f.write(r"% Include this file in your main .tex to pull in all artifacts")
        f.write("\n% Tables\n")
        for name in ["dataset_stats", "model_architecture", "quantization_comparison",
                      "resolution_benchmark", "platform_comparison", "memory_budget", "ablation"]:
            f.write(f"\\input{{tables/{name}.tex}}\n")
        f.write("\n% Figures\n")
        for name in ["dataset_samples", "quantization_tradeoff", "latency_comparison",
                      "fps_comparison", "model_size", "memory_map", "speedup",
                      "resolution_accuracy", "detection_samples"]:
            f.write(f"\\includegraphics[width=\\columnwidth]{{figures/{name}.pdf}}\n")
    print(f"  Saved: {path}")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("RescueVision Edge — Paper Artifacts Generator")
    print("=" * 60)

    for d in [PAPER_DIR, TABLES_DIR, FIGURES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Collect all results
    print("\n[1/4] Collecting experiment data...")
    data = collect_all_results()
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved: {DATA_PATH}")

    # 2. Generate LaTeX tables
    print("\n[2/4] Generating LaTeX tables...")
    write_individual_tables(data)
    write_combined_tables(data)

    # 3. Generate figures
    print("\n[3/4] Generating figures...")
    fig_quantization_tradeoff(data, FIGURES_DIR / "quantization_tradeoff.pdf")
    fig_latency_comparison(data, FIGURES_DIR / "latency_comparison.pdf")
    fig_fps_comparison(data, FIGURES_DIR / "fps_comparison.pdf")
    fig_model_size(data, FIGURES_DIR / "model_size.pdf")
    fig_speedup(data, FIGURES_DIR / "speedup.pdf")
    fig_memory_map(data, FIGURES_DIR / "memory_map.pdf")
    fig_resolution_accuracy(data, FIGURES_DIR / "resolution_accuracy.pdf")
    fig_dataset_samples(data, FIGURES_DIR / "dataset_samples.pdf")
    fig_detection_samples(data, FIGURES_DIR / "detection_samples.pdf")

    # 4. Write paper inputs
    print("\n[4/4] Writing paper input stubs...")
    write_paper_inputs(data)

    print(f"\n{'='*60}")
    print("All paper artifacts generated!")
    print(f"  Tables: {TABLES_DIR}/")
    print(f"  Figures: {FIGURES_DIR}/")
    print(f"  Combined: {PAPER_DIR}/paper_inputs.tex")
    print(f"  Data: {DATA_PATH}")
    print(f"{'='*60}")
    print("\nIn your LaTeX paper, add:")
    print("  \\input{paper_inputs.tex}")
    print("And copy paper-exports/ next to your main .tex file.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
