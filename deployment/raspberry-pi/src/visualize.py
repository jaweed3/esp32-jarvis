#!/usr/bin/env python3
"""
Visualize benchmark results: generate comparison tables and charts.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_results(path):
    with open(path) as f:
        return json.load(f)


def plot_latency_comparison(all_results, output_dir):
    """Bar chart: latency across platforms and resolutions."""
    fig, ax = plt.subplots(figsize=(10, 6))

    platforms = list(all_results.keys())
    resolutions = ["192x192", "256x256", "320x320"]
    x = np.arange(len(resolutions))
    width = 0.25

    for i, (platform, data) in enumerate(all_results.items()):
        latencies = []
        for res in resolutions:
            w, h = res.split("x")
            latency = data.get("resolution_benchmarks", {}).get(res, {}).get("mean_latency_ms")
            if latency is None:
                latency = data.get("tflite_int8", {}).get("resolution_benchmarks", {}).get(res, {}).get("mean_latency_ms")
            latencies.append(latency if latency else 0)
        ax.bar(x + i * width, latencies, width, label=platform)

    ax.set_xlabel("Input Resolution")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Inference Latency by Platform & Resolution")
    ax.set_xticks(x + width)
    ax.set_xticklabels(resolutions)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    path = output_dir / "latency_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def plot_fps_comparison(all_results, output_dir):
    """Bar chart: FPS across platforms and resolutions."""
    fig, ax = plt.subplots(figsize=(10, 6))

    platforms = list(all_results.keys())
    resolutions = ["192x192", "256x256", "320x320"]
    x = np.arange(len(resolutions))
    width = 0.25

    for i, (platform, data) in enumerate(all_results.items()):
        fps_values = []
        for res in resolutions:
            fps = data.get("resolution_benchmarks", {}).get(res, {}).get("fps")
            if fps is None:
                fps = data.get("tflite_int8", {}).get("resolution_benchmarks", {}).get(res, {}).get("fps")
            fps_values.append(fps if fps else 0)
        ax.bar(x + i * width, fps_values, width, label=platform)

    ax.set_xlabel("Input Resolution")
    ax.set_ylabel("FPS")
    ax.set_title("Throughput by Platform & Resolution")
    ax.set_xticks(x + width)
    ax.set_xticklabels(resolutions)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    path = output_dir / "fps_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def plot_model_size(all_results, output_dir):
    """Bar chart: model size comparison."""
    fig, ax = plt.subplots(figsize=(8, 5))

    platforms = []
    sizes = []
    for platform, data in all_results.items():
        for variant in ["tflite_fp32", "tflite_int8"]:
            size = data.get(variant, {}).get("file_size_mb")
            if size:
                platforms.append(f"{platform}\n{variant.replace('tflite_', '').upper()}")
                sizes.append(size)

    ax.bar(range(len(sizes)), sizes, color=["#6495ED", "#FF6347"])
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels(platforms, fontsize=8)
    ax.set_ylabel("Model Size (MB)")
    ax.set_title("Model Size: FP32 vs INT8")
    ax.grid(axis="y", alpha=0.3)

    for i, v in enumerate(sizes):
        ax.text(i, v + 0.1, f"{v:.2f}", ha="center", fontsize=9)

    path = output_dir / "model_size.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def generate_latex_table(all_results):
    """Generate a LaTeX table summarizing results."""
    lines = [
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{RescueVision Edge: Performance Comparison Across Platforms}",
        "\\label{tab:benchmark}",
        "\\begin{tabular}{|l|c|c|c|c|c|}",
        "\\hline",
        "Platform & Precision & Resolution & FPS & Latency (ms) & Size (MB) \\\\",
        "\\hline",
    ]

    for platform, data in all_results.items():
        for variant in ["tflite_fp32", "tflite_int8"]:
            vdata = data.get(variant, {})
            if not vdata:
                continue
            precision = "FP32" if "fp32" in variant else "INT8"
            size = vdata.get("file_size_mb", "N/A")
            first_row = True
            for res, bench in vdata.get("resolution_benchmarks", {}).items():
                fps = bench.get("fps", "N/A")
                lat = bench.get("mean_latency_ms", "N/A")
                plat_label = f"{platform}" if first_row else ""
                lines.append(
                    f"  {plat_label} & {precision} & {res} & {fps} & {lat} & {size} \\\\"
                )
                first_row = False
            lines.append("  \\hline")

    lines.extend([
        "\\end{tabular}",
        "\\end{table}",
    ])

    return "\n".join(lines)


def generate_markdown_table(all_results, output_dir):
    """Generate a readable markdown comparison table."""
    lines = [
        "# RescueVision Edge — Benchmark Results\n",
        "| Platform | Precision | Resolution | FPS | Latency (ms) | Size (MB) |",
        "|----------|-----------|------------|-----|---------------|-----------|",
    ]

    for platform, data in all_results.items():
        for variant in ["tflite_fp32", "tflite_int8"]:
            vdata = data.get(variant, {})
            if not vdata:
                continue
            precision = "FP32" if "fp32" in variant else "INT8"
            size = vdata.get("file_size_mb", "N/A")
            res_benches = vdata.get("resolution_benchmarks", {})
            if res_benches:
                for res, bench in res_benches.items():
                    fps = bench.get("fps", "N/A")
                    lat = bench.get("mean_latency_ms", "N/A")
                    lines.append(
                        f"| {platform} | {precision} | {res} | {fps} | {lat} ms | {size} MB |"
                    )
            else:
                lines.append(
                    f"| {platform} | {precision} | N/A | N/A | N/A | {size} MB |"
                )

    lines.append("")

    path = output_dir / "benchmark_table.md"
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved: {path}")


def main():
    output_dir = Path(__file__).resolve().parent.parent / "results"
    output_dir.mkdir(exist_ok=True)

    # Collect all results
    all_results = {}

    # PC results
    pc_path = Path(__file__).resolve().parent.parent.parent / "training" / "evaluation_results"
    pc_file = pc_path / "results_full_evaluation.json"
    if pc_file.exists():
        all_results["PC (GPU)"] = json.load(open(pc_file))

    # RPi results
    rpi_file = output_dir / "rpi_benchmark.json"
    if rpi_file.exists():
        all_results["Raspberry Pi 4"] = json.load(open(rpi_file))

    if not all_results:
        print("No results found. Run benchmarks first.")
        return

    # Generate charts
    plot_latency_comparison(all_results, output_dir)
    plot_fps_comparison(all_results, output_dir)
    plot_model_size(all_results, output_dir)
    generate_markdown_table(all_results, output_dir)

    # LaTeX table
    latex = generate_latex_table(all_results)
    with open(output_dir / "benchmark_table.tex", "w") as f:
        f.write(latex)
    print(f"Saved: {output_dir / 'benchmark_table.tex'}")

    print("\nDone! Visualizations saved to", output_dir)


if __name__ == "__main__":
    main()
