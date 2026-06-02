#!/usr/bin/env python3
"""
Run YOLOv8n INT8 detection on a single image or camera stream on RPi.
"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def load_model(tflite_path):
    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    return interpreter, input_details, output_details


def detect(interpreter, input_details, output_details, image, conf_thresh=0.25):
    h, w = image.shape[:2]
    input_size = input_details["shape"][1]

    # Preprocess
    resized = cv2.resize(image, (input_size, input_size))
    if input_details["dtype"] == np.uint8:
        inp = resized.astype(np.uint8)
    else:
        inp = (resized.astype(np.float32) / 255.0)

    # Inference
    interpreter.set_tensor(input_details["index"], inp[np.newaxis, ...])
    interpreter.invoke()
    output = interpreter.get_tensor(output_details["index"])

    # Post-process (simplified YOLOv8)
    output = np.squeeze(output)
    boxes = output[:4, :]
    scores = output[4:5, :]  # person class only
    person_scores = scores[0]

    mask = person_scores > conf_thresh
    if not np.any(mask):
        return []

    boxes = boxes[:, mask]
    scores = person_scores[mask]

    # [cx, cy, w, h] → [x1, y1, x2, y2]
    cx, cy, bw, bh = boxes
    x1 = ((cx - bw / 2) * input_size).astype(int)
    y1 = ((cy - bh / 2) * input_size).astype(int)
    x2 = ((cx + bw / 2) * input_size).astype(int)
    y2 = ((cy + bh / 2) * input_size).astype(int)

    # Scale to original image
    scale_x = w / input_size
    scale_y = h / input_size
    detections = []
    for i in range(len(scores)):
        detections.append({
            "bbox": [
                int(x1[i] * scale_x), int(y1[i] * scale_y),
                int(x2[i] * scale_x), int(y2[i] * scale_y),
            ],
            "confidence": float(scores[i]),
            "class": 0,
            "label": "person",
        })
    return detections


def draw_detections(image, detections):
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        conf = det["confidence"]
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, f"person {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="model/model_int8.tflite")
    parser.add_argument("--image", help="Path to input image")
    parser.add_argument("--camera", action="store_true", help="Use Pi camera")
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    interpreter, input_details, output_details = load_model(args.model)

    if args.image:
        img = cv2.imread(args.image)
        dets = detect(interpreter, input_details, output_details, img, args.conf)
        print(f"Detections: {len(dets)}")
        for d in dets:
            print(f"  {d['label']}: {d['confidence']:.3f} @ {d['bbox']}")
        result = draw_detections(img, dets)
        cv2.imwrite("output.jpg", result)
        print("Saved: output.jpg")

    if args.camera:
        try:
            from picamera2 import Picamera2
            picam = Picamera2()
            picam.configure(picam.create_preview_configuration(
                main={"size": (640, 480)}))
            picam.start()
        except ImportError:
            print("picamera2 not available, using OpenCV VideoCapture")
            cap = cv2.VideoCapture(0)

        while True:
            if "picam" in dir():
                frame = picam.capture_array()
            else:
                ret, frame = cap.read()
                if not ret:
                    break

            dets = detect(interpreter, input_details, output_details,
                         frame, args.conf)
            frame = draw_detections(frame, dets)
            cv2.imshow("RescueVision Edge", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
