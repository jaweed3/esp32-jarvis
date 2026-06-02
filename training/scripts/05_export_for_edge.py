#!/usr/bin/env python3
"""
05_export_for_edge.py — Export quantized TFLite model for edge deployment.

Creates:
1. TFLite INT8 model → C header array for ESP32-S3 (TFLite Micro)
2. TFLite INT8 → RPi deployment package
3. Model metadata JSON (input shape, dtype, label map)
4. Visualization of sample detections
"""

import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils
from utils import QUANTIZED_DIR, DATASET_DIR


def convert_to_c_array(tflite_path: Path, output_path: Path, var_name: str = "model_tflite"):
    """Convert TFLite model binary to C header array for ESP32-S3."""
    with open(tflite_path, "rb") as f:
        model_data = f.read()

    # Generate C header
    lines = [
        "#ifndef MODEL_DATA_H",
        "#define MODEL_DATA_H",
        "",
        f"#ifdef __cplusplus",
        f"extern \"C\" {{",
        f"#endif",
        "",
        f"const unsigned char {var_name}[] = {{",
    ]

    # Write bytes in rows of 12
    for i in range(0, len(model_data), 12):
        chunk = model_data[i:i+12]
        hex_bytes = ", ".join(f"0x{b:02x}" for b in chunk)
        lines.append(f"  {hex_bytes},")

    lines.extend([
        "};",
        f"const unsigned int model_tflite_len = {len(model_data)};",
        "",
        f"#ifdef __cplusplus",
        f"}}",
        f"#endif",
        "",
        "#endif  // MODEL_DATA_H",
    ])

    output_path.write_text("\n".join(lines) + "\n")
    print(f"C header written to {output_path}")
    print(f"  Array size: {len(model_data)} bytes ({len(model_data) / 1024:.1f} KB)")

    return output_path


def export_model_metadata(tflite_path: Path, output_path: Path, imgsz: int):
    """Export model metadata JSON for deployment."""
    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    metadata = {
        "model": "YOLOv8n INT8 Quantized",
        "description": "RescueVision Edge victim detection model",
        "input": {
            "shape": input_details["shape"].tolist(),
            "dtype": str(input_details["dtype"]),
            "quantization": {
                "scale": float(input_details["quantization"][0]),
                "zero_point": int(input_details["quantization"][1]),
            } if input_details["quantization"] else None,
        },
        "output": {
            "shape": output_details["shape"].tolist(),
            "dtype": str(output_details["dtype"]),
            "quantization": {
                "scale": float(output_details["quantization"][0]),
                "zero_point": int(output_details["quantization"][1]),
            } if output_details["quantization"] else None,
        },
        "classes": ["person"],
        "input_size": imgsz,
        "recommended_conf_threshold": 0.25,
        "recommended_iou_threshold": 0.5,
        "framework": "TFLite Micro",
        "target_hardware": "ESP32-S3",
    }

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model metadata written to {output_path}")
    return metadata


def prepare_rpi_package(tflite_path: Path, output_dir: Path):
    """Copy TFLite model + labels to RPi deployment dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy2(tflite_path, output_dir / "model_int8.tflite")

    # Label map
    with open(output_dir / "labels.txt", "w") as f:
        f.write("person\n")

    print(f"RPi deployment package prepared in {output_dir}")


def visualize_sample_detections(tflite_path: Path, output_dir: Path,
                                 val_images, val_paths, imgsz: int,
                                 n_samples: int = 5):
    """Run inference on sample images and draw detection overlays."""
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    output_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(min(n_samples, len(val_images))):
        img = val_images[idx]
        orig = (img * 255).astype(np.uint8)

        # Prepare input
        inp = cv2.resize(orig, (imgsz, imgsz))
        if input_details[0]["dtype"] == np.uint8:
            inp = inp.astype(np.uint8)
        else:
            inp = (inp.astype(np.float32) / 255.0)

        # Inference
        interpreter.set_tensor(input_details[0]["index"], inp[np.newaxis, ...])
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]["index"])

        # Post-process
        from scripts.03_quantize import postprocess_yolo_output
        boxes, scores, _ = postprocess_yolo_output(output, conf_thresh=0.25, imgsz=imgsz)

        # Draw
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        ax.imshow(cv2.cvtColor(orig, cv2.COLOR_RGB2BGR) if len(orig.shape) == 3 else orig)

        if len(boxes):
            for box, score in zip(boxes, scores):
                x1, y1, x2, y2 = box
                h_scale = orig.shape[0] / imgsz
                w_scale = orig.shape[1] / imgsz
                rect = plt.Rectangle(
                    (x1 * w_scale, y1 * h_scale),
                    (x2 - x1) * w_scale,
                    (y2 - y1) * h_scale,
                    fill=False, edgecolor="lime", linewidth=2,
                )
                ax.add_patch(rect)
                ax.text(x1 * w_scale, y1 * h_scale - 5,
                        f"person {score:.2f}",
                        color="lime", fontsize=10,
                        bbox=dict(facecolor="black", alpha=0.5))

        ax.set_title(f"Detection Sample {idx+1}")
        ax.axis("off")

        save_path = output_dir / f"detection_sample_{idx+1}.png"
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {save_path}")


def main():
    print("=" * 60)
    print("RescueVision Edge — Export for Edge Deployment")
    print("=" * 60)

    cfg = utils.load_config()
    imgsz = cfg["model"]["imgsz"]

    tflite_int8 = QUANTIZED_DIR / "yolov8n_int8.tflite"
    if not tflite_int8.exists():
        print("INT8 TFLite model not found. Run 03_quantize.py first.")
        return

    ESP32_INCLUDE_DIR = PROJECT_ROOT.parent / "deployment" / "esp32-s3" / "include"
    RPI_DIR = PROJECT_ROOT.parent / "deployment" / "raspberry-pi" / "model"
    EXPORT_DIR = QUANTIZED_DIR / "exported"

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. C header for ESP32-S3
    print("\n[1/3] Generating C header for ESP32-S3...")
    convert_to_c_array(
        tflite_int8,
        ESP32_INCLUDE_DIR / "model_data.h",
        var_name="model_tflite",
    )

    # 2. Model metadata
    print("\n[2/3] Exporting model metadata...")
    export_model_metadata(tflite_int8, EXPORT_DIR / "model_metadata.json", imgsz)

    # 3. RPi deployment package
    print("\n[3/3] Preparing RPi deployment package...")
    prepare_rpi_package(tflite_int8, RPI_DIR)

    # 4. Visualization (if validation data available)
    val_img_dir = DATASET_DIR / "images" / "val"
    val_paths = sorted(val_img_dir.glob("*"))[:10]
    if val_paths:
        print("\nGenerating sample detection visualizations...")
        import cv2
        val_images = []
        for p in val_paths:
            img = cv2.imread(str(p))
            if img is not None:
                val_images.append(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if val_images:
            visualize_sample_detections(
                tflite_int8, EXPORT_DIR / "visualizations",
                np.array(val_images), val_paths, imgsz, n_samples=5
            )

    print(f"\n{'='*60}")
    print("Export Complete!")
    print(f"{'='*60}")
    print(f"  ESP32-S3 C header: {ESP32_INCLUDE_DIR / 'model_data.h'}")
    print(f"  Model metadata: {EXPORT_DIR / 'model_metadata.json'}")
    print(f"  RPi deployment: {RPI_DIR}")
    print(f"  Visualizations: {EXPORT_DIR / 'visualizations'}")


if __name__ == "__main__":
    main()
