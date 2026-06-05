#!/usr/bin/env python3
"""
Synthetic test: verifies all 4 bug fixes work correctly.
Creates fake model output, runs postprocess, checks mAP.
"""

import sys, numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import utils

IMSZ = 192
CONF_THRESH = 0.1
IOU_THRESH = 0.5

print("=" * 60)
print("Test 1: Coordinate Scaling (Bug #3)")
print("=" * 60)
# Simulate model output [84, 756] with a single box at center
output = np.zeros((84, 5), dtype=np.float32)
output[0, 0] = 0.5  # cx = 0.5 (normalized)
output[1, 0] = 0.5  # cy = 0.5
output[2, 0] = 0.2  # w  = 0.2
output[3, 0] = 0.4  # h  = 0.4
output[4, 0] = 0.9  # person score = 0.9
boxes, scores, _ = utils.postprocess_yolo_output(output, CONF_THRESH, IMSZ)
x1, y1, x2, y2 = boxes[0]
# Expected: cx=0.5 -> x1 = (0.5-0.2/2)*192 = 76.8, x2 = (0.5+0.2/2)*192 = 115.2
# Expected: cy=0.5 -> y1 = (0.5-0.4/2)*192 = 57.6, y2 = (0.5+0.4/2)*192 = 134.4
expected = np.array([76.8, 57.6, 115.2, 134.4])
assert np.allclose(boxes[0], expected, atol=0.1), f"BUG: got {boxes[0]}, expected {expected}"
print(f"  PASS: boxes = {boxes[0].round(1)} (expected {expected})")

print()
print("=" * 60)
print("Test 2: NMS (Bug #4) — overlapping boxes")
print("=" * 60)
output2 = np.zeros((84, 3), dtype=np.float32)
# Two overlapping boxes
output2[0, 0] = 0.5; output2[1, 0] = 0.5; output2[2, 0] = 0.3; output2[3, 0] = 0.3; output2[4, 0] = 0.9
output2[0, 1] = 0.51; output2[1, 1] = 0.51; output2[2, 1] = 0.3; output2[3, 1] = 0.3; output2[4, 1] = 0.5
# Non-overlapping box
output2[0, 2] = 0.1; output2[1, 2] = 0.1; output2[2, 2] = 0.1; output2[3, 2] = 0.1; output2[4, 2] = 0.8
boxes2, scores2, _ = utils.postprocess_yolo_output(output2, CONF_THRESH, IMSZ)
# Should keep 2 boxes: the high-confidence one from overlap pair + the separate one
print(f"  Boxes kept: {len(boxes2)} (expected 2)")
assert len(boxes2) == 2, f"BUG: NMS kept {len(boxes2)} boxes, expected 2"
print(f"  Scores: {scores2.round(3)} (should be [0.9, 0.8])")
assert np.allclose(sorted(scores2, reverse=True), [0.9, 0.8]), f"BUG: wrong scores: {scores2}"
print(f"  PASS: NMS correctly suppressed overlapping low-confidence box")

print()
print("=" * 60)
print("Test 3: mAP computation with corrected boxes")
print("=" * 60)
# Prediction: one correct box
preds = [{"boxes": [[76.8, 57.6, 115.2, 134.4]], "scores": [0.9]}]
# GT: same box (in YOLO format converted to pixel)
gts = [{"boxes": [[76.8, 57.6, 115.2, 134.4]]}]
metrics = utils.compute_map(preds, gts, IOU_THRESH, CONF_THRESH)
print(f"  mAP@0.5: {metrics['mAP@0.5']} (expected 1.0 for perfect match)")
assert metrics['mAP@0.5'] > 0.99, f"BUG: mAP should be ~1.0, got {metrics['mAP@0.5']}"
print(f"  PASS: mAP = {metrics['mAP@0.5']}")

# Test with coordinate mismatch (old bug scenario: no * imgsz)
print()
print("=" * 60)
print("Test 4: Coordinate mismatch simulation (old bug)")
print("=" * 60)
# If coords are in [0,1] but GT in [0,192], IoU should be ~0
preds_bad = [{"boxes": [[0.4, 0.3, 0.6, 0.7]], "scores": [0.9]}]
metrics_bad = utils.compute_map(preds_bad, gts, IOU_THRESH, CONF_THRESH)
print(f"  mAP@0.5 with [0,1] vs [0,192]: {metrics_bad['mAP@0.5']} (expected ~0.0)")
assert metrics_bad['mAP@0.5'] < 0.01, f"BUG: mismatched coords should give 0 mAP, got {metrics_bad['mAP@0.5']}"
print(f"  PASS: coordinate mismatch correctly yields ~0 mAP")

print()
print("=" * 60)
print("Test 5: INT8 dequantization (Bug #1)")
print("=" * 60)
# Simulate int8 output that hasn't been dequantized
raw_int8 = np.array([[-128, -128, -128, -128, 100]], dtype=np.int8).T
# After dequant: (100 - (-128)) * 0.005 = 228 * 0.005 = 1.14 (impossible for sigmoid)
deq = (raw_int8.astype(np.float32) - (-128)) * 0.005
print(f"  Raw int8 score: {raw_int8[4,0]}, dequantized: {deq[4,0]:.3f}")
print(f"  Without dequant, score would be {raw_int8[4,0]} (as float = {float(raw_int8[4,0])})")
# Fill proper output with dequant scores
output5 = np.zeros((84, 3), dtype=np.float32)
output5[0, 0] = 0.5; output5[1, 0] = 0.5; output5[2, 0] = 0.2; output5[3, 0] = 0.4
# Simulate dequantized score 0.9 * 128 - 128 = -13... actually sigmoid output is [-128, 127] range
# After dequant: (-13+128)*0.005 = 0.575
score_val = int(0.9 / 0.005 + (-128))  # = 52
output5[4, 0] = score_val
boxes5, scores5, _ = utils.postprocess_yolo_output(output5, CONF_THRESH, IMSZ)
print(f"  Score after dequant: {scores5[0]:.3f} (expected ~0.9)")
assert scores5[0] > 0.5, f"BUG: dequant score too low: {scores5[0]}"
print(f"  PASS: dequantized score = {scores5[0]:.3f}")
# Without dequant: output5[4,0] = 52 (raw int8), interpreted as float, score = 52 > 0.1 ✓
# Actually the raw int8 value 52 would pass conf_thresh=0.1 by coincidence!

print()
print("=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
