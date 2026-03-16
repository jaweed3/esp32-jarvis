
# ESP32-S3 Sense — Wake Word & Face Recognition 

This repository contains an **edge AI project** built on **Seeed Studio XIAO ESP32-S3 Sense**, focusing on **wake word detection** and **face recognition** running directly on-device.

The project explores **low-power, real-time AI inference** on microcontrollers using **TinyML** and **embedded computer vision**, with the goal of building an always-on, privacy-preserving smart edge system.

## ✨ Features 

### 🔊 Wake Word Detection
- Always-on wake word detection
- On-device audio processing
- Lightweight ML model optimized for ESP32-S3
- Low-latency inference
- No cloud dependency

### 👤 Face Recognition
- Face detection using onboard camera
- Face embedding & recognition (edge-based)
- Real-time inference
- Privacy-first (no image upload)

### ⚙️ System-Level
- Fully on-device inference (Edge AI)
- Optimized for limited RAM & compute
- Modular pipeline (audio → vision → logic)
- Designed for real-world embedded use cases

---

## 🧠 Hardware

- **Board**: Seeed Studio XIAO ESP32-S3 Sense
- **MCU**: ESP32-S3 (Dual-core Xtensa LX7)
- **Camera**: OV2640
- **Microphone**: Built-in digital mic
- **Connectivity**: WiFi / Bluetooth
- **Acceleration**: ESP-DSP / NN acceleration (planned)

---

## 🧰 Software Stack

- **Framework**: ESP-IDF
- **Language**: C / C++
- **ML**:
  - TensorFlow Lite for Microcontrollers (planned)
  - Custom DSP for audio preprocessing
- **Vision**:
  - ESP32 camera driver
  - Lightweight face detection pipeline
- **Build System**: CMake (ESP-IDF native)

---

## 🏗️ Project Structure (WIP)

```text
.
├── audio/
│   ├── wake_word/
│   └── dsp/
├── vision/
│   ├── face_detection/
│   └── face_recognition/
├── models/
│   ├── wake_word/
│   └── face/
├── firmware/
│   └── main/
├── scripts/
├── docs/
└── README.md
````

---

## 🚀 Getting Started (Early Stage)

### Prerequisites

* ESP-IDF installed
* XIAO ESP32-S3 Sense connected
* USB cable (data)

```bash
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

> ⚠️ Note: Some modules may not compile yet due to ongoing development.

---

## 🧪 Current Progress

* [x] Board setup & flashing
* [x] Camera initialization
* [ ] Audio input pipeline (basic)
* [ ] Wake word ML model integration
* [ ] Face detection optimization
* [ ] Face recognition embeddings
* [ ] Power optimization
* [ ] End-to-end demo

---

## 🎯 Use Cases (Target)

* Smart access control
* Voice-activated embedded systems
* Offline biometric authentication
* Edge AI research & prototyping
* Privacy-preserving smart devices

---

## 🔒 Privacy & Edge AI Philosophy

This project is designed with a **privacy-first approach**:

* No cloud inference
* No external data transmission
* All processing happens locally on the device

---

## 📌 Notes

* This is an **experimental / research-oriented project**
* Performance is constrained by MCU resources
* Accuracy and latency are actively being optimized

---

## 📄 License

MIT License (TBD)

---

## 🙌 Acknowledgements

* Espressif Systems
* Seeed Studio
* TinyML & Edge AI community

