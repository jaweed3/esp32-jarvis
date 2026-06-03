#!/usr/bin/env python3
"""Download real COCO images to replace blank placeholders."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BASE_URLS = [
    "http://images.cocodataset.org/val2017",
    "http://images.cocodataset.org/train2017",
]

for split in ["train", "val", "test"]:
    img_dir = PROJECT_ROOT / "dataset" / "images" / split
    if not img_dir.exists():
        print(f"{img_dir} not found, skipping")
        continue

    jpgs = sorted(img_dir.glob("*.jpg"))
    if not jpgs:
        print(f"{split}: no images found")
        continue

    existing = [p for p in jpgs if p.stat().st_size > 10000]
    print(f"{split}: {len(jpgs)} total, {len(existing)} already real")

    for i, jpg in enumerate(jpgs):
        if jpg.stat().st_size > 10000:
            continue

        fname = jpg.name
        ok = False
        for base in BASE_URLS:
            url = f"{base}/{fname}"
            ret = subprocess.run(
                ["wget", "-q", url, "-O", str(jpg)],
                capture_output=True, timeout=30
            )
            if ret.returncode == 0:
                ok = True
                break

        if not ok:
            print(f"  FAILED: {fname}")
        elif (i + 1) % 50 == 0:
            kb = jpg.stat().st_size / 1024
            print(f"  [{i+1}/{len(jpgs)}] {fname} ({kb:.0f} KB)")

    print(f"  Done: {split}")

print("All downloads complete.")
