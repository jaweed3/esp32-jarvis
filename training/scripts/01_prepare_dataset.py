#!/usr/bin/env python3
"""
01_prepare_dataset.py — Download COCO person subset and prepare YOLO-format dataset.

Steps:
1. Download COCO 2017 train/val annotations & images
2. Filter images containing "person" class
3. Split into train/val/test (80/15/5)
4. Convert to YOLO label format (class_id cx cy w h normalized)
5. Save to dataset/ directory structure expected by ultralytics
"""

import json
import shutil
import random
from pathlib import Path
from collections import defaultdict
from urllib.request import urlretrieve
import zipfile

import yaml
from tqdm import tqdm
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
CONFIG_DIR = PROJECT_ROOT / "configs"

COCO_ANNOTATIONS_URL = (
    "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
)
COCO_TRAIN_URL = (
    "http://images.cocodataset.org/zips/train2017.zip"
)

PERSON_CLASS_ID = 1  # COCO person class ID
MAX_IMAGES = 2000
SEED = 42

random.seed(SEED)


def download_coco_subset():
    """Download minimal COCO data needed for person detection."""
    raw_dir = DATASET_DIR / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Download annotations (~250MB)
    ann_zip = raw_dir / "annotations_trainval2017.zip"
    if not ann_zip.exists():
        print("Downloading COCO annotations (~250MB)...")
        urlretrieve(COCO_ANNOTATIONS_URL, ann_zip)
    else:
        print("Annotations zip exists, skipping download.")

    # Extract annotations
    ann_dir = raw_dir / "annotations"
    if not ann_dir.exists():
        print("Extracting annotations...")
        with zipfile.ZipFile(ann_zip, "r") as z:
            z.extractall(raw_dir)

    # Download subset of training images if needed
    img_zip = raw_dir / "train2017.zip"
    if not img_zip.exists():
        print(
            "COCO images not found locally. "
            "Downloading full train2017.zip (~18GB) is impractical."
        )
        print("We'll use synthetic/label-only setup for now.")
        print(
            "To use real images: download train2017.zip manually, "
            "place in dataset/_raw/, and rerun."
        )
        return False

    print("Extracting images...")
    with zipfile.ZipFile(img_zip, "r") as z:
        z.extractall(raw_dir)

    return True


def load_coco_annotations(ann_file: Path) -> dict:
    """Load COCO JSON and index person images."""
    with open(ann_file) as f:
        coco = json.load(f)

    # Build category id → supercategory mapping
    cat_id_to_name = {cat["id"]: cat["name"] for cat in coco["categories"]}
    print(f"Categories: {len(coco['categories'])}")

    # Index images that contain person
    image_to_annotations = defaultdict(list)
    for ann in tqdm(coco["annotations"], desc="Indexing annotations"):
        if ann["category_id"] == PERSON_CLASS_ID:
            image_to_annotations[ann["image_id"]].append(ann)

    # Build image info lookup
    image_info = {img["id"]: img for img in coco["images"]}

    # Filter to only person images with valid annotations
    person_images = []
    for img_id, anns in image_to_annotations.items():
        img = image_info.get(img_id)
        if img is None:
            continue
        # Filter out images with degenerate boxes
        valid_anns = []
        for ann in anns:
            bbox = ann["bbox"]  # [x, y, w, h]
            if bbox[2] > 0 and bbox[3] > 0:
                valid_anns.append(ann)
        if valid_anns:
            person_images.append((img, valid_anns))

    print(f"Found {len(person_images)} images containing 'person'")
    return person_images, image_info


def convert_bbox_coco_to_yolo(bbox, img_w: int, img_h: int) -> list:
    """COCO [x, y, w, h] → YOLO [cx, cy, w, h] normalized."""
    x, y, w, h = bbox
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    wn = w / img_w
    hn = h / img_h
    # Clamp to [0, 1]
    cx = max(0, min(1, cx))
    cy = max(0, min(1, cy))
    wn = max(0, min(1, wn))
    hn = max(0, min(1, hn))
    return [cx, cy, wn, hn]


def write_yolo_dataset(person_images, image_info, has_images: bool, src_img_dir: Path):
    """Write dataset in YOLO format with train/val/test splits."""
    random.shuffle(person_images)

    n_total = min(len(person_images), MAX_IMAGES)
    n_train = int(n_total * 0.80)
    n_val = int(n_total * 0.15)
    n_test = n_total - n_train - n_val

    splits = {
        "train": person_images[:n_train],
        "val": person_images[n_train : n_train + n_val],
        "test": person_images[n_train + n_val : n_train + n_val + n_test],
    }

    for split_name, split_data in splits.items():
        img_dir = DATASET_DIR / "images" / split_name
        lbl_dir = DATASET_DIR / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for img, anns in tqdm(split_data, desc=f"Writing {split_name}"):
            img_id = img["id"]
            file_name = img["file_name"]
            img_w, img_h = img["width"], img["height"]

            # Copy image if available
            if has_images:
                src = src_img_dir / file_name
                dst = img_dir / file_name
                if src.exists():
                    shutil.copy2(src, dst)

            # Write label file
            label_path = lbl_dir / Path(file_name).with_suffix(".txt")
            with open(label_path, "w") as f:
                for ann in anns:
                    bbox = ann["bbox"]
                    cx, cy, wn, hn = convert_bbox_coco_to_yolo(bbox, img_w, img_h)
                    f.write(f"0 {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}\n")

    print(f"\nDataset splits:")
    for split_name in splits:
        img_dir = DATASET_DIR / "images" / split_name
        lbl_dir = DATASET_DIR / "labels" / split_name
        n_imgs = len(list(img_dir.glob("*" if DATASET_DIR.exists() else "*")))
        n_labels = len(list(lbl_dir.glob("*.txt")))
        print(f"  {split_name}: {n_labels} labels")


def create_dataset_yaml():
    """Write the dataset YAML for ultralytics."""
    config = {
        "path": str(DATASET_DIR.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": {0: "person"},
    }
    yaml_path = CONFIG_DIR / "rescuevision.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Dataset YAML written to {yaml_path}")


def main():
    print("=" * 60)
    print("RescueVision Edge — Dataset Preparation")
    print("=" * 60)

    has_images = download_coco_subset()

    ann_file = (
        DATASET_DIR / "_raw" / "annotations" / "instances_train2017.json"
    )
    if not ann_file.exists():
        print(f"Annotations not found at {ann_file}")
        print("Using synthetic label generation...")
        _generate_synthetic_dataset()
        return

    person_images, image_info = load_coco_annotations(ann_file)

    if len(person_images) == 0:
        print("No person images found. Generating synthetic data...")
        _generate_synthetic_dataset()
        return

    src_img_dir = DATASET_DIR / "_raw" / "train2017"
    write_yolo_dataset(person_images, image_info, has_images, src_img_dir)
    create_dataset_yaml()

    print("\nDone! Dataset ready for training.")


def _generate_synthetic_dataset():
    """Generate synthetic person detection dataset for development/testing."""
    print("Generating synthetic person detection dataset...")
    from PIL import Image, ImageDraw

    splits = {"train": 1600, "val": 300, "test": 100}

    for split_name, count in splits.items():
        img_dir = DATASET_DIR / "images" / split_name
        lbl_dir = DATASET_DIR / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            h, w = 192, 192
            img = Image.new("RGB", (w, h), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)

            n_persons = random.randint(1, 3)
            label_lines = []
            for _ in range(n_persons):
                pw = random.randint(30, 80)
                ph = random.randint(60, 140)
                px = random.randint(0, w - pw)
                py = random.randint(0, h - ph)

                draw.rectangle([px, py, px + pw, py + ph], fill=(200, 100, 100))

                cx = (px + pw / 2) / w
                cy = (py + ph / 2) / h
                nw = pw / w
                nh = ph / h
                label_lines.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            img.save(img_dir / f"synth_{i:04d}.png")

            with open(lbl_dir / f"synth_{i:04d}.txt", "w") as f:
                f.write("\n".join(label_lines))

        print(f"  {split_name}: {count} synthetic images")

    create_dataset_yaml()
    print("\nSynthetic dataset ready for development training.")


if __name__ == "__main__":
    main()
