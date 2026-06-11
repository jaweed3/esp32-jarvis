#!/usr/bin/env python3
"""Build Ultimatics-formatted DOCX from paper content."""

import os
import sys

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    os.system("pip install python-docx -q")
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATE = "/Users/wedjaw/project/esp32/template.docx"
OUTPUT = "/Users/wedjaw/project/esp32/paper_ultimatics.docx"

doc = Document(TEMPLATE)

# Clear content
for p in list(doc.paragraphs):
    p._element.getparent().remove(p._element)
for t in list(doc.tables):
    t._element.getparent().remove(t._element)

# Page setup
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(3)
section.left_margin = Cm(3)
section.bottom_margin = Cm(2)
section.right_margin = Cm(2)


def run_font(run, name="Times New Roman", size=10, bold=False, italic=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic


def add_p(text, size=10, bold=False, italic=False, align=None,
          before=0, after=3, indent=None):
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    if indent:
        p.paragraph_format.first_line_indent = Cm(indent)
    run = p.add_run(text)
    run_font(run, size=size, bold=bold, italic=italic)
    return p


def section_heading(text, before=8, after=4):
    return add_p(text.upper(), size=10, bold=True, before=before, after=after)


def sub_heading(text):
    return add_p(text, size=10, bold=True, italic=True, before=5, after=2)


def body(text):
    return add_p(text, size=10, before=0, after=3, indent=0.5)


# === TITLE ===
title = ("Analisis dan Benchmark Deployment YOLOv8n INT8 pada ESP32-S3: "
         "Optimasi Progressive")
add_p(title, size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)

# === AUTHORS ===
add_p("Jaweed\u00b9, Dihin Muriyatmoko\u00b2", size=10,
      align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
add_p("\u00b9Program Studi Informatika, Universitas Darussalam Gontor, Indonesia",
      size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
add_p("\u00b2Program Studi Informatika, Universitas Darussalam Gontor, Indonesia",
      size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
add_p("Email: jaweed@unida.gontor.ac.id",
      size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)

# === ABSTRACT ===
abstract = (
    "This study analyzes the feasibility of deploying an INT8 quantized YOLOv8n model "
    "on the ESP32-S3 microcontroller for single-class object detection. The model was trained on a "
    "COCO 2017 person subset (1,600 train, 300 val) at 192\u00d7192 resolution and quantized via "
    "post-training quantization (PTQ) to INT8, yielding a model size of 3.08 MB with 4.41% mAP@0.5. "
    "Three-stage progressive optimization was performed: (1) baseline TFLite Micro reference kernels "
    "at 219.3 s per inference; (2) ESP-NN SIMD-optimized Conv2D kernels reducing latency to 18.0 s "
    "(12.2\u00d7 speedup); (3) a custom LUT-based LOGISTIC kernel further reducing latency to 7.2 s "
    "(total 30.4\u00d7 speedup). Operator profiling revealed the LOGISTIC operation consumed 62.3% of "
    "execution time before optimization. The measured tensor arena of 510 KB (98.5% below theoretical "
    "worst-case) confirms the model fits within the ESP32-S3 memory budget of 8 MB PSRAM and 8 MB flash. "
    "Estimated power consumption is 549 mW during inference. "
    "These results provide a reference benchmark for deploying YOLO-based detectors on Xtensa LX7 MCUs."
)
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
p.paragraph_format.space_after = Pt(3)
p.paragraph_format.line_spacing = 1.0
r1 = p.add_run("Abstract\u2014")
run_font(r1, bold=True, italic=True)
r2 = p.add_run(abstract)
run_font(r2, italic=True)

# === INDEX TERMS ===
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(8)
p.paragraph_format.line_spacing = 1.0
r1 = p.add_run("Index Terms\u2014")
run_font(r1, bold=True, italic=True)
r2 = p.add_run("ESP32-S3; object detection; post-training quantization; TinyML; YOLOv8n")
run_font(r2, italic=True)

# === 1. INTRODUCTION ===
section_heading("1. Introduction")
body(
    "Deep learning has enabled real-time object detection across various computing platforms [1]\u2013[4]. "
    "However, most detection models require expensive, power-hungry GPU-class hardware. In recent years, "
    "the TinyML paradigm [5] has emerged as an alternative by running inference models on low-power "
    "microcontrollers (MCUs), enabling edge applications such as environmental monitoring, anomaly "
    "detection, and industrial automation without cloud dependency [6], [7]."
)
body(
    "The ESP32-S3 is a compelling MCU for computer vision applications: it provides dual-core Xtensa LX7 "
    "at 240 MHz, 8 MB flash, 8 MB PSRAM, camera support, and WiFi connectivity\u2014at under $10 USD. "
    "Despite these capabilities, running deep learning models such as YOLO on the ESP32-S3 faces "
    "significant challenges: limited memory, constrained compute throughput, and operator support that "
    "is less extensive than desktop frameworks."
)
body(
    "This study answers the following research question: to what extent can a quantized YOLOv8n model "
    "be efficiently deployed on the ESP32-S3 microcontroller? The key contributions are: (1) a systematic "
    "analysis of the training, quantization, and deployment pipeline for INT8 YOLOv8n on ESP32-S3; "
    "(2) progressive optimization driven by operator profiling\u2014identifying the LOGISTIC bottleneck "
    "(62.3% of runtime), optimizing Conv2D via ESP-NN SIMD (12.2\u00d7 speedup), and implementing a "
    "LUT-based LOGISTIC kernel (additional 2.5\u00d7 speedup), yielding a total 30.4\u00d7 improvement "
    "over the reference baseline; (3) comprehensive memory characterization on physical hardware; "
    "and (4) all research artifacts released openly for reproducibility."
)

# === 2. RELATED WORK ===
section_heading("2. Related Work")
body(
    "Deploying CNNs on microcontrollers has been an active topic since CMSIS-NN [8] for ARM Cortex-M "
    "and TFLite Micro [9] as a cross-platform inference framework. MCUNet [6] demonstrated that "
    "MCU-optimized architectures can achieve competitive accuracy at low resolution. "
    "MicroNets [10] introduced neural architecture search (NAS) specifically for MCU constraints."
)
body(
    "YOLO [1]\u2013[4] remains the dominant object detection architecture, with the nano variant "
    "(YOLOv8n, 3.0M parameters) designed for resource-constrained deployment. Edge-YOLO [11] proposed "
    "edge-specific optimizations but focused on ARM and embedded GPU platforms rather than low-end MCUs."
)
body(
    "Post-training quantization (PTQ) [12]\u2013[14] has proven effective for reducing model size and "
    "improving inference speed. Deep Compression [15] demonstrated that combining pruning, quantization, "
    "and Huffman coding can drastically reduce model size. In the MCU domain, MobileNet [16] and "
    "MobileNetV2 [17] are commonly used as backbones due to their computational efficiency."
)
body(
    "For the ESP32, ESP-NN [18] provides optimized neural network kernels using Xtensa LX7 SIMD "
    "extensions. However, systematic evaluations of YOLOv8n deployment on the ESP32-S3 with detailed "
    "memory and operator profiling remain limited. This study fills that gap."
)

# === 3. METHOD ===
section_heading("3. Method")

sub_heading("A. Dataset")
body(
    "We used the person subset of COCO 2017 [19], consisting of 1,599 training, 300 validation, and "
    "100 test images. The 192\u00d7192 input resolution was chosen as the minimum resolution preserving "
    "person-level detail while minimizing computation on the ESP32-S3."
)

sub_heading("B. Model Architecture and Training")
body(
    "We adopted YOLOv8n [4], the nano variant with 3.0M parameters and 8.1 GFLOPs. Training proceeded "
    "in two stages: 50 epochs with a frozen backbone (transfer learning from COCO pretrained weights) "
    "followed by 50 epochs of full fine-tuning at 192\u00d7192. The AdamW optimizer was used with a "
    "learning rate of 0.001 and cosine decay. The PyTorch baseline achieved 45.59% mAP@0.5. After "
    "conversion through PyTorch\u2192ONNX\u2192TensorFlow\u2192TFLite, the TFLite FP32 model achieved "
    "12.26% mAP@0.5\u2014a 33.33 pp drop attributable to numerical differences in the export pipeline."
)

sub_heading("C. Post-Training Quantization")
body(
    "Post-training quantization (PTQ) [12]\u2013[14] was performed using TensorFlow Lite with a "
    "representative dataset of 200 images. The FP32 TFLite model (3.01 MB) was converted to INT8 "
    "(3.08 MB) with INT8 inference type and uint8 input/output tensors. The additional 7.85 pp mAP@0.5 "
    "drop from TFLite FP32 (12.26%) to INT8 (4.41%) represents a significant accuracy degradation, "
    "largely due to the low 192\u00d7192 resolution where a person occupying 10% of image height spans "
    "only 19 pixels."
)

sub_heading("D. ESP32-S3 Deployment")
body(
    "The firmware was developed using PlatformIO with the Arduino framework and TFLite Micro on a "
    "Seeed XIAO ESP32S3 Sense (240 MHz CPU, 8 MB flash, 8 MB PSRAM). The INT8 model was compiled as "
    "a C array (3,386,338 bytes) and stored in flash. Three kernel configurations were benchmarked "
    "progressively: (1) reference TFLite Micro kernels; (2) ESP-NN SIMD-optimized Conv2D kernels via "
    "Xtensa LX7 SIMD extensions; and (3) ESP-NN with a custom LUT-based LOGISTIC kernel."
)

# === 4. RESULTS AND DISCUSSION ===
section_heading("4. Results and Discussion")

sub_heading("A. Operator Profiling and Optimization")
body(
    "The reference kernel configuration yielded 219,287 ms per inference\u2014impractical for any "
    "application. ESP-NN Conv2D integration reduced latency to 18,020 ms (12.2\u00d7 speedup). "
    "Operator profiling using TFLite Micro\u2019s MicroProfiler revealed a counter-intuitive finding: "
    "the LOGISTIC (sigmoid) operation consumed 62.3% of total latency (11,758 ms), while Conv2D "
    "accounted for only 35.2% (6,634 ms). This is because LOGISTIC was not covered by ESP-NN and "
    "executed via the naive reference implementation."
)
body(
    "We implemented an ESP-NN LOGISTIC wrapper kernel using esp_nn_logistic_s8(), which evaluates "
    "sigmoid via a 256-byte lookup table in O(1) per element. After optimization, inference latency "
    "dropped to 7,216 ms (2.5\u00d7 additional speedup), yielding a total 30.4\u00d7 improvement over "
    "the reference baseline. At this point, Conv2D accounts for approximately 92% of remaining latency; "
    "the LOGISTIC overhead was effectively eliminated."
)

sub_heading("B. Accuracy")
body(
    "The INT8 model achieved 4.41% mAP@0.5 at 192\u00d7192, down from 12.26% (TFLite FP32). "
    "At this resolution, a person occupying 10% of image height spans only 19 pixels, limiting "
    "discriminative features. The accuracy is suitable for coarse region-of-interest flagging "
    "(approximately 8 frames per minute at 7.2 s latency) but insufficient for fully autonomous "
    "detection in cluttered scenes."
)

sub_heading("C. Memory Characterization")
body(
    "A key finding is that the measured tensor arena was only 510 KB, dramatically lower than the "
    "theoretical worst-case estimate of 34.1 MB\u2014a 98.5% reduction due to TFLite Micro\u2019s "
    "memory planner reusing tensor buffers across subgraphs. Total RAM footprint (arena 510 KB + "
    "frame buffer 225 KB + stack and RTOS ~100 KB = 835 KB) fits entirely within the 8 MB PSRAM. "
    "Model weights (3.3 MB) fit within the 8 MB flash budget."
)

sub_heading("D. Power Consumption")
body(
    "Based on ESP32-S3 datasheet parameters at 240 MHz, the estimated power consumption during "
    "inference is 549 mW (chip) / 646 mW (USB). Full pipeline operation (inference + camera + WiFi) "
    "is estimated at 1,308 mW. A 2S 1,000 mAh battery would sustain approximately 1\u20132 hours of "
    "continuous inference. These figures are model-based estimates; empirical measurement using an "
    "INA219 current sensor remains future work."
)

sub_heading("E. Discussion and Limitations")
body(
    "The results reveal a clear accuracy\u2013speed\u2013size trade-off. The dominant bottleneck after "
    "optimization is Conv2D (~92% of latency), which is already running ESP-NN SIMD-optimized kernels; "
    "further gains require model architectural changes. The study has several limitations: (1) the "
    "modest 4.41% mAP@0.5 restricts autonomous operation; (2) the 7.2 s inference latency does not "
    "meet real-time requirements; (3) power figures are datasheet-based estimates; and (4) no "
    "end-to-end camera integration was performed on the physical hardware."
)

# === 5. CONCLUSION ===
section_heading("5. Conclusion")
body(
    "This study demonstrated that an INT8 quantized YOLOv8n model can be deployed on the ESP32-S3 "
    "microcontroller at 7.2 s per inference and 549 mW estimated power consumption, through progressive "
    "operator-level optimization achieving 30.4\u00d7 total speedup over the reference baseline. The "
    "measured tensor arena of 510 KB confirms memory feasibility. A key finding\u2014the LOGISTIC "
    "operator consuming 62.3% of latency before optimization\u2014highlights the importance of "
    "operator profiling in TinyML system development."
)
body(
    "Future work includes: (i) exploring shallower YOLO backbones or structured pruning to reduce "
    "Conv2D workload; (ii) evaluating resolution-accuracy trade-offs at 160\u00d7160 and 128\u00d7128; "
    "(iii) integrating the OV2640 camera for end-to-end pipeline testing; and (iv) empirical power "
    "measurement using an INA219 current sensor."
)

# === ACKNOWLEDGMENT ===
section_heading("Acknowledgment", before=4)
body(
    "The authors thank the anonymous reviewers for their constructive feedback that improved "
    "the quality of this manuscript."
)

# === REFERENCES ===
section_heading("References", before=8)

refs = [
    '[1] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once: Unified, real-time object detection," in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2016, pp. 779\u2013788.',
    '[2] J. Redmon and A. Farhadi, "YOLOv3: An incremental improvement," arXiv preprint arXiv:1804.02767, 2018.',
    '[3] A. Bochkovskiy, C.-Y. Wang, and H.-Y. M. Liao, "YOLOv4: Optimal speed and accuracy of object detection," arXiv preprint arXiv:2004.10934, 2020.',
    '[4] G. Jocher, A. Chaurasia, and J. Qiu, "Ultralytics YOLO," GitHub, 2023. [Online]. Available: https://github.com/ultralytics/ultralytics',
    '[5] P. Warden and D. Situnayake, TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers. O\u2019Reilly Media, 2019.',
    '[6] J. Lin et al., "MCUNet: Tiny deep learning on IoT devices," in Proc. Adv. Neural Inf. Process. Syst. (NeurIPS), 2020.',
    '[7] C. Banbury et al., "Benchmarking TinyML systems: Challenges and direction," arXiv preprint arXiv:2003.04821, 2020.',
    '[8] L. Lai, N. Suda, and V. Chandra, "CMSIS-NN: Efficient neural network kernels for Arm Cortex-M CPUs," arXiv preprint arXiv:1801.06601, 2018.',
    '[9] R. David et al., "TensorFlow Lite Micro: Embedded machine learning on TinyML systems," in Proc. Mach. Learn. Syst. (MLSys), 2021.',
    '[10] C. Banbury et al., "MicroNets: Neural network architectures for deploying TinyML applications on commodity microcontrollers," in Proc. Mach. Learn. Syst. (MLSys), 2021.',
    '[11] S. Xu et al., "Edge-YOLO: Real-time object detection on edge devices," arXiv preprint arXiv:2209.13083, 2022.',
    '[12] B. Jacob et al., "Quantization and training of neural networks for efficient integer-arithmetic-only inference," in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2018, pp. 2704\u20132713.',
    '[13] R. Krishnamoorthi, "Quantizing deep convolutional networks for efficient inference: A whitepaper," arXiv preprint arXiv:1806.08342, 2018.',
    '[14] A. Gholami et al., "A survey of quantization methods for efficient neural network inference," arXiv preprint arXiv:2103.13630, 2021.',
    '[15] S. Han, H. Mao, and W. J. Dally, "Deep compression: Compressing deep neural networks with pruning, trained quantization and Huffman coding," in Proc. Int. Conf. Learn. Represent. (ICLR), 2016.',
    '[16] A. G. Howard et al., "MobileNets: Efficient convolutional neural networks for mobile vision applications," arXiv preprint arXiv:1704.04861, 2017.',
    '[17] M. Sandler et al., "MobileNetV2: Inverted residuals and linear bottlenecks," in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2018, pp. 4510\u20134518.',
    '[18] Espressif Systems, "ESP-NN: Optimised neural network functions for Espressif chips," GitHub, 2023. [Online]. Available: https://github.com/espressif/esp-nn',
    '[19] T.-Y. Lin et al., "Microsoft COCO: Common objects in context," in Proc. Eur. Conf. Comput. Vis. (ECCV), 2014.',
    '[20] N. Zhang et al., "Training a disaster victim detection network for UAV search and rescue using harmonious composite images," Remote Sens., vol. 14, no. 13, p. 2977, 2022.',
]

for ref in refs:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    run = p.add_run(ref)
    run_font(run, size=9)

doc.save(OUTPUT)
print(f"OK: {OUTPUT} ({os.path.getsize(OUTPUT)} bytes)")
print(f"Judul kata: {len(title.split())}")
print(f"Abstrak kata: {len(abstract.split())}")
print(f"Referensi: {len(refs)}")
