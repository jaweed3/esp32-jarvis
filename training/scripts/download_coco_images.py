#!/usr/bin/env python3
"""Download real COCO images to replace blank placeholders (parallel)."""

import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BASE_URLS = [
    "http://images.cocodataset.org/train2017",
    "http://images.cocodataset.org/val2017",
]


def download_one(jpg: Path) -> tuple[str, bool]:
    if jpg.stat().st_size > 10000:
        return (jpg.name, True)
    for base in BASE_URLS:
        url = f"{base}/{jpg.name}"
        ret = subprocess.run(
            ["wget", "-q", "--timeout=15", "--tries=2", url, "-O", str(jpg)],
            capture_output=True, timeout=60,
        )
        if ret.returncode == 0:
            return (jpg.name, True)
    return (jpg.name, False)


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
    need = [p for p in jpgs if p.stat().st_size <= 10000]
    print(f"{split}: {len(jpgs)} total, {len(existing)} real, {len(need)} to download")

    if not need:
        print(f"  All real already")
        continue

    done = len(existing)
    failed = 0
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(download_one, jpg): jpg for jpg in need}
        for f in as_completed(futures):
            name, ok = f.result()
            if ok:
                done += 1
            else:
                failed += 1
            if (done + failed) % 100 == 0:
                print(f"  [{done}/{len(jpgs)}] ({failed} failed)")

    print(f"  Done: {split} ({done}/{len(jpgs)}, {failed} failed)")

print("All downloads complete.")
