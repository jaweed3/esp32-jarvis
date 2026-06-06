# Peer Review — RescueVision Edge Paper

**Target:** IEEE Embedded Systems Letters (4-page limit) / HardwareX

**Review date:** 2026-06-06

---

## Summary

Paper presents INT8-quantized YOLOv8n person detection on ESP32-S3 for SAR victim detection. Contributions: (1) complete PTQ pipeline, (2) accuracy-speed-size trade-off analysis, (3) ESP-NN + LOGISTIC LUT achieving 30.4× speedup (219s → 7.2s), (4) memory characterization (510 KB arena, 98.5% below theoretical).

---

## 3 Blockers (must fix before submission)

### B1: PyTorch → TFLite FP32 Accuracy Gap

| Metric | Value |
|--------|-------|
| PyTorch FP32 mAP@0.5 | 45.59% |
| TFLite FP32 mAP@0.5 | 12.26% |
| **Drop** | **33.33 pp** |
| TFLite INT8 mAP@0.5 | 4.41% |

**Problem:** The 33 pp drop from PyTorch to TFLite FP32 is unexplained. This is the largest accuracy degradation in the pipeline (33 pp vs 7.85 pp for INT8 quantization). Without isolating the root cause, the signal-to-noise ratio is poor: INT8 quantization appears to "lose" 7.85 pp, but the pipeline itself already lost 33 pp before quantization.

**Action required:**
1. Reproduce TFLite FP32 output logits from PyTorch output logits on same inputs
2. Measure cosine similarity / MSE per layer through ONNX export
3. If the gap is confirmed as a pipeline fidelity issue (not a bug), document the root cause quantitatively in the paper
4. If fixable (e.g., post-processing mismatch as we found in bugs #1-4), re-run evaluation and update mAP numbers

**Status:** ⚠️ 4 evaluation bugs already fixed (dequantization, INT8 input quantization, coordinate scaling, NMS). Re-evaluation blocked — needs dataset on remote server.

---

### B2: Insufficient References

| Before | After |
|--------|-------|
| 5 references | **20 references** |

**Fix applied:** Added 16 new verified references across 6 categories:
- YOLO lineage (yolov1 CVPR 2016, yolov3, yolov4)
- Quantization (Jacob et al. CVPR 2018, Krishnamoorthi, Gholami survey)
- TinyML/MCU (MCUNet NeurIPS, CMSIS-NN, MicroNets MLSys, TinyML benchmark)
- Efficient CNNs (MobileNets, MobileNetV2 CVPR, Deep Compression ICLR)
- ESP32 hardware + ESP-NN (datasheet, GitHub)
- SAR victim detection (Zhang et al. Remote Sensing 2022)

**Status:** ✅ Done.

---

### B3: Accuracy Justification

**Problem:** The paper claims SAR victim detection but reports only 4.41% mAP@0.5 at 192×192. For a life-critical application, this number raises red flags. The paper must clearly scope the claim.

**Action required:**
1. Explicitly state that 4.41% mAP is suitable for **coarse victim localization** (flagging ROIs for human review), not autonomous detection
2. Acknowledge the resolution limitation (192×192 → person at 10% height ≈ 19 pixels)
3. Frame contributions as **feasibility + memory characterization**, not production-ready accuracy
4. If re-evaluation with fixed bugs changes mAP, incorporate the new number

---

## 3 Major Issues (deferred / future work)

### I1: Power Measurements — Model-Based Only

**Problem:** All power figures are from ESP32-S3 datasheet estimates, not empirical INA219 measurements. The paper includes a full table (Table VI) with "chip mW" and "USB mW" columns, but these are speculative.

**Current text (paper.tex:94-103):**
> "Based on ESP32-S3 datasheet parameters at 240 MHz... These are model-based estimates derived from datasheet specifications; empirical measurements on physical hardware remain future work."

**Impact:** A reviewer will flag this. For IEEE ESL, model-based estimates may be acceptable if transparently labeled (which we do).

**Recommendation:** Defer to future work. The INA219 module exists but was not integrated.

---

### I2: No Camera Integration

**Problem:** All benchmarks use synthetic input (memset 128). OV2640 camera initializes correctly ("Camera initialized: QVGA (320x240) JPEG") but JPEG-to-RGB decoding and pipeline integration not implemented.

**Impact:** The "victim detection" claim cannot be demonstrated with real camera images. For a hardware journal, this weakens the demonstration.

**Recommendation:** Defer. Paper scope is inference feasibility + memory characterization on physical MCU.

---

### I3: No Comparison Platform

**Problem:** Only PC GPU (RTX 3060) vs ESP32-S3. Missing standard embedded baselines:
- Raspberry Pi 4 (Cortex-A72, Linux)
- Jetson Nano (GPU-accelerated)
- Coral USB TPU (edge TPU accelerator)
- Arduino Portenta (Cortex-M7)

**Impact:** Readers cannot contextualize the ESP32-S3's 7.2s inference relative to other edge platforms.

**Recommendation:** Defer. RPi 4 comparison was planned but required hardware setup that was deprioritized.

---

## Additional Notes

### Paper Structure
- Abstract needs to explicitly state the scope (feasibility study, not production system)
- Related Work section is thin — partially addressed by B2 (new references)
- Limitations section (sec:conclusion) already acknowledges all 3 major issues — good

### Figures
- latency_comparison.pdf: FP32 vs INT8 on RTX 3060 only — add ESP32-S3 bar if possible
- power_breakdown.pdf: useful but caveat that these are estimates

### Checklist for Submission
- [ ] B1: Fix or quantify PyTorch→TFLite gap
- [x] B2: 16 new references added (was 5, now 20)
- [ ] B3: Justify accuracy in abstract + intro
- [ ] I1: Acknowledge power as estimates (already done)
- [ ] I2: Acknowledge no camera (already done)
- [ ] I3: Acknowledge no comparison (already done)
- [ ] Compile with correct journal template (IEEE ESL or HardwareX)
- [ ] Page count ≤ 4 (IEEE ESL) or ≤ 8 (HardwareX)
