#!/usr/bin/env python3
"""
07_power_estimation.py — ESP32-S3 Power Model & Measurement.

Two modes:
  1. Model-based estimation (no hardware needed) — uses datasheet specs +
     activity factors to estimate power per subsystem.
  2. INA219 reader — parses serial logs from ESP32-S3 with INA219 sensor.

Outputs:
  - power_breakdown.json
  - power_comparison.pdf (bar chart: idle vs camera vs inference)
  - power_timeline.pdf (if real measurement available)
  - power_budget.tex (LaTeX table for paper)
"""

import json, time
from pathlib import Path
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import BASELINE_DIR, QUANTIZED_DIR

PAPER_DIR = PROJECT_ROOT / "paper-exports"
FIGURES_DIR = PAPER_DIR / "figures"
TABLES_DIR = PAPER_DIR / "tables"

matplotlib.rcParams.update({
    "font.family": "serif", "font.size": 10, "axes.labelsize": 11,
    "axes.titlesize": 12, "legend.fontsize": 9, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "figure.dpi": 150, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
})

# ── ESP32-S3 Datasheet Constants ──────────────────────────
V_CORE    = 3.3   # V (typical operating voltage)
V_USB     = 5.0   # V (USB input, through LDO)
LDO_EFF   = 0.85  # LDO efficiency

class PowerModel:
    """ESP32-S3 power estimation based on active peripherals."""

    # Current draw (mA) per subsystem @ 3.3V, 240MHz
    # Sources: ESP32-S3 datasheet, ESP-IDF power management docs
    SUBSYSTEMS = OrderedDict({
        "CPU active (single)":    (35, 55),    # min, max mA
        "CPU active (dual)":      (55, 85),
        "PSRAM access":           (15, 25),
        "Flash read":              (8, 15),
        "Camera (OV2640)":        (40, 60),
        "WiFi TX (streaming)":   (150, 210),
        "WiFi RX":                (80, 120),
        "TFLite inference":       (30, 50),    # additional over CPU
        "I2S microphone":         (5, 10),
        "LED indicator":          (2, 5),
        "Base (LDO + misc)":      (20, 30),
    })

    SCENARIOS = OrderedDict({
        "Deep sleep":     ["Base (LDO + misc)"],
        "Idle (camera)":  ["Base (LDO + misc)", "Camera (OV2640)"],
        "Idle (no cam)":  ["Base (LDO + misc)"],
        "Camera + WiFi":  ["Base (LDO + misc)", "CPU active (dual)",
                           "Camera (OV2640)", "WiFi TX (streaming)",
                           "PSRAM access", "Flash read"],
        "Inference only": ["Base (LDO + misc)", "CPU active (dual)",
                           "PSRAM access", "Flash read",
                           "TFLite inference"],
        "Inference + Cam":["Base (LDO + misc)", "CPU active (dual)",
                           "Camera (OV2640)", "PSRAM access", "Flash read",
                           "TFLite inference"],
        "Full pipeline":  ["Base (LDO + misc)", "CPU active (dual)",
                           "Camera (OV2640)", "WiFi TX (streaming)",
                           "PSRAM access", "Flash read",
                           "TFLite inference"],
    })

    def estimate_scenario(self, scenario: str, mode: str = "typical") -> dict:
        """Estimate power for a given scenario."""
        subs = self.SCENARIOS.get(scenario, [])
        if mode == "min":
            f = lambda r: r[0]
        elif mode == "max":
            f = lambda r: r[1]
        else:  # typical = midpoint
            f = lambda r: (r[0] + r[1]) / 2

        breakdown = {}
        total_ma = 0
        for name in subs:
            if name in self.SUBSYSTEMS:
                i = f(self.SUBSYSTEMS[name])
                breakdown[name] = i
                total_ma += i

        p_chip = total_ma * V_CORE / 1000  # W
        p_usb = p_chip / LDO_EFF
        return {
            "scenario": scenario,
            "mode": mode,
            "total_ma": round(total_ma, 1),
            "power_chip_mw": round(p_chip * 1000, 1),
            "power_usb_mw": round(p_usb * 1000, 1),
            "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
        }

    def estimate_all(self) -> list:
        results = []
        for scen in self.SCENARIOS:
            for mode in ["min", "typical", "max"]:
                results.append(self.estimate_scenario(scen, mode))
        return results

    def estimate_fp32_vs_int8(self) -> dict:
        """Compare power during FP32 vs INT8 inference."""
        inference_active = self.estimate_scenario("Inference only", "typical")
        # INT8 uses less PSRAM bandwidth → lower current
        int8_factor = 0.85  # 15% reduction in dynamic current
        int8_power = {**inference_active}
        int8_power["total_ma"] = round(inference_active["total_ma"] * int8_factor, 1)
        int8_power["power_chip_mw"] = round(int8_power["total_ma"] * V_CORE, 1)
        int8_power["power_usb_mw"] = round(int8_power["power_chip_mw"] / LDO_EFF, 1)
        int8_power["note"] = "Estimated 15% reduction from reduced PSRAM bandwidth"
        return {"FP32": inference_active, "INT8": int8_power}


def fig_power_comparison(data: list, path: Path):
    """Bar chart: power across scenarios."""
    scenarios = [
        "Deep sleep", "Idle (camera)", "Camera + WiFi",
        "Inference only", "Inference + Cam", "Full pipeline"
    ]
    labels_short = [s.replace(" ", "\n") for s in scenarios]

    typical = []
    for s in scenarios:
        r = next(x for x in data if x["scenario"] == s and x["mode"] == "typical")
        typical.append(r["power_chip_mw"])

    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E", "#57737A"]

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.bar(labels_short, typical, color=colors, edgecolor="black", linewidth=0.5, width=0.6)

    for bar, v in zip(bars, typical):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                f"{v:.0f}", ha="center", fontsize=8)

    ax.set_ylabel("Power (mW)")
    ax.set_title("ESP32-S3 Power Consumption by Operating Scenario")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_power_breakdown(scenario: str, breakdown: dict, path: Path):
    """Pie chart: power breakdown by subsystem for a given scenario."""
    names = list(breakdown.keys())
    values = list(breakdown.values())

    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(
        values, labels=names, autopct="%1.0f%%",
        startangle=90, textprops={"fontsize": 8},
    )
    ax.set_title(f"Power Breakdown — {scenario}")

    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def fig_fp32_vs_int8_power(comparison: dict, path: Path):
    """Bar chart: FP32 vs INT8 power comparison."""
    fig, ax = plt.subplots(figsize=(4, 3.5))
    variants = ["FP32", "INT8"]
    values = [comparison["FP32"]["power_chip_mw"],
              comparison["INT8"]["power_chip_mw"]]
    colors = ["#4A72AF", "#E15759"]

    bars = ax.bar(variants, values, color=colors, edgecolor="black", linewidth=0.5, width=0.4)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{v:.0f} mW", ha="center", fontsize=10)

    savings = (1 - values[1] / values[0]) * 100
    ax.annotate(f"{savings:.0f}% less", xy=(1, values[1]),
                xytext=(0.5, values[0] * 1.1), fontsize=9,
                arrowprops=dict(arrowstyle="->", lw=1.5),
                ha="center")

    ax.set_ylabel("Power (mW)")
    ax.set_title("Inference Power: FP32 vs INT8")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def tab_power_budget(scenarios: list) -> str:
    """Generate LaTeX table of power per scenario."""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{ESP32-S3 Power Consumption (Typical @ 3.3\,V, 240\,MHz)}",
        r"\label{tab:power}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Operating Scenario & Current (mA) & Chip Power (mW) & USB Power (mW) \\",
        r"\midrule",
    ]
    for s in scenarios:
        if s["mode"] == "typical":
            lines.append(
                f"  {s['scenario']} & {s['total_ma']} & "
                f"{s['power_chip_mw']} & {s['power_usb_mw']} \\\\"
            )
    lines.extend([
        r"\midrule",
        r"\multicolumn{4}{l}{\footnotesize USB power estimated at 85\% LDO efficiency} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def parse_ina219_log(log_path: Path) -> list:
    """Parse serial log from ESP32-S3 with INA219 sensor output."""
    records = []
    with open(log_path) as f:
        for line in f:
            if "INA219" in line:
                # Expected format: "INA219: V=3.30V I=0.250A P=825mW"
                try:
                    parts = line.strip().split()
                    v = float(parts[1].replace("V=", "").replace("V", ""))
                    i = float(parts[2].replace("I=", "").replace("A", ""))
                    p = float(parts[3].replace("P=", "").replace("mW", ""))
                    records.append({"V": v, "I": i, "P": p, "raw": line.strip()})
                except (IndexError, ValueError):
                    continue
    return records


def fig_power_timeline(records: list, path: Path):
    """Line chart: power over time from INA219."""
    if not records:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No INA219 data available.\nFlash ESP32-S3 with power_monitor and capture serial log.",
                ha="center", va="center", fontsize=10, transform=ax.transAxes)
        ax.axis("off")
        fig.savefig(path)
        plt.close(fig)
        print(f"  (placeholder) Saved: {path}")
        return

    times = np.arange(len(records))
    powers = [r["P"] for r in records]
    currents = [r["I"] * 1000 for r in records]  # A → mA

    fig, ax1 = plt.subplots(figsize=(8, 3.5))
    ax1.plot(times, powers, color="#E15759", linewidth=1)
    ax1.set_ylabel("Power (mW)", color="#E15759")
    ax1.tick_params(axis="y", labelcolor="#E15759")

    ax2 = ax1.twinx()
    ax2.plot(times, currents, color="#4A72AF", linewidth=0.8, alpha=0.6)
    ax2.set_ylabel("Current (mA)", color="#4A72AF")
    ax2.tick_params(axis="y", labelcolor="#4A72AF")

    ax1.set_xlabel("Sample (≈100ms interval)")
    ax1.set_title("ESP32-S3 Power Draw During Inference")
    ax1.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved: {path}")


def main():
    print("=" * 60)
    print("RescueVision Edge — Power Estimation")
    print("=" * 60)

    model = PowerModel()
    results_dir = PROJECT_ROOT / "power_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Model estimation
    print("\n[1/3] Estimating power from ESP32-S3 datasheet model...")
    all_scenarios = model.estimate_all()
    comparison = model.estimate_fp32_vs_int8()

    data = {
        "model": "ESP32-S3 @ 240MHz, 3.3V",
        "scenarios": all_scenarios,
        "fp32_vs_int8": comparison,
        "ina219_data": None,
    }
    with open(results_dir / "power_breakdown.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {results_dir / 'power_breakdown.json'}")

    # 2. Try to load INA219 data if available
    ina_path = PROJECT_ROOT.parent / "deployment" / "esp32-s3" / "results" / "power_serial.log"
    if ina_path.exists():
        print(f"\n[2/3] Parsing INA219 log from {ina_path}...")
        records = parse_ina219_log(ina_path)
        data["ina219_data"] = records
        print(f"  Parsed {len(records)} records")
    else:
        print(f"\n[2/3] No INA219 log found. Skipping real measurement.")
        records = []

    # 3. Generate outputs
    print("\n[3/3] Generating figures and tables...")
    fig_power_comparison(all_scenarios, FIGURES_DIR / "power_comparison.pdf")
    fig_fp32_vs_int8_power(comparison, FIGURES_DIR / "power_fp32_vs_int8.pdf")
    fig_power_timeline(records, FIGURES_DIR / "power_timeline.pdf")

    # Power breakdown for the most important scenario
    full = next(s for s in all_scenarios
                if s["scenario"] == "Full pipeline" and s["mode"] == "typical")
    fig_power_breakdown("Full Pipeline", full["breakdown"],
                        FIGURES_DIR / "power_breakdown.pdf")

    # LaTeX table
    latex = tab_power_budget(all_scenarios)
    with open(TABLES_DIR / "power_budget.tex", "w") as f:
        f.write(latex)
    print(f"  Saved: {TABLES_DIR / 'power_budget.tex'}")

    # Print summary
    print(f"\n{'='*60}")
    print("Power Summary (Typical)")
    print(f"{'='*60}")
    for s in all_scenarios:
        if s["mode"] == "typical":
            print(f"  {s['scenario']:<22s} → {s['total_ma']:>5.1f} mA  "
                  f"{s['power_chip_mw']:>5.0f} mW chip  "
                  f"{s['power_usb_mw']:>5.0f} mW USB")
    print(f"\n  INT8 saves ~{100 - int(comparison['INT8']['power_chip_mw'] / comparison['FP32']['power_chip_mw'] * 100)}% "
          f"power vs FP32 during inference")
    print(f"  Figures: {FIGURES_DIR}/")
    print(f"  Table: {TABLES_DIR / 'power_budget.tex'}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
