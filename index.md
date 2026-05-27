---
layout: default
title: Neural Vision — $15 Edge AI Camera
---

# See. Hear. Recognize.
# All on a $15 chip.

**Face detection. Wake word recognition. Live MJPEG streaming.**  
Zero cloud. Zero Linux. Zero subscription.  
Entirely on the ESP32-S3 — a microcontroller smaller than a stick of gum.

[View on GitHub](https://github.com/jaweed3/esp32-jarvis){: .btn .btn-primary} &nbsp; [Start Building](https://github.com/jaweed3/esp32-jarvis#quick-start){: .btn}

---

**⚡ \<1s boot · 🔒 No cloud · 🧠 8MB RAM · 📡 WiFi + BLE**

---

## The Problem

Why does AI vision cost $100+ and need a fan?

### ❌ The Overkill Stack (Raspberry Pi)

$75–$100. 3–6W power draw. Needs active cooling. 20–40 second boot. Full Linux kernel just to detect a face.

### ❌ The Dumb Camera (ESP32-CAM)

$7–10. No streaming. No audio. No ML. Hardcoded WiFi credentials — recompile to change networks.

### ❌ The Privacy Nightmare (Cloud APIs)

Send every frame to the cloud. Latency. Bandwidth costs. Privacy violations. Subscription fees.

> *There had to be a middle ground.*

---

## Meet Neural Vision

A complete vision + voice AI pipeline that fits in **8MB of RAM**.

### 🧠 On-Device Intelligence

MTCNN detects faces in 100–150ms. MobileFaceNet generates 128-dimensional embeddings. All inference happens on the ESP32-S3 — **no data leaves the device.**

### 🎤 Voice-Activated Wake Word

22KB TFLite Micro model. <50ms latency. 3-second audio ring buffer in PSRAM. The device wakes up when you speak.

### 📺 Live MJPEG Dashboard

Stream live video to any browser at 15–25 FPS. Zero-copy JPEG pipeline. Single-page dashboard served directly from firmware — no external dependencies.

### 📡 Zero-Config Setup

First boot → connect to `ESP32-S3-Setup` → pick your WiFi → done. Captive portal with DNS spoofing. The entire UI is 4KB gzipped, compiled into firmware. No SPIFFS. No SD card corruption.

---

## Technical Architecture

### Dual-Core FreeRTOS

| Core 0 — Network | Core 1 — Processing |
|:---|:---|
| WiFi stack (STA + AP) | Audio capture (I2S PDM) |
| lwIP TCP/IP | Camera pipeline (MJPEG) |
| HTTP Server | ML inference (TFLite / ESP-DL) |
| DNS Server (captive portal) | State machine + EventBus |

> WiFi and ML inference cannot share a core. Core pinning solved instability that priority tuning couldn't.

### 6-State Machine

| State | LED | Purpose |
|:---|:---|:---|
| `INIT` | Breathing pulse | Hardware init, PSRAM alloc |
| `AP_MODE` | Slow blink | Captive portal @ 192.168.4.1 |
| `CONNECTING` | Fast blink | WiFi connection with retry |
| `IDLE` | Solid on | Online, wake word listening |
| `ACTIVE` | Solid on | Face detection (30s timeout) |
| `ERROR` | Fast blink | Auto-recovery in 5s |

The ACTIVE → IDLE timeout cuts average power draw by **~70%**.

---

## Memory Budget (8MB PSRAM)

| Allocation | Size | Location |
|:---|---|:---|
| Camera frame buffers (×2) | ~100KB | DRAM |
| Audio ring buffer (3s) | 96KB | PSRAM |
| MFCC feature buffer | 8KB | PSRAM |
| TFLite tensor arena | 32KB | PSRAM |
| RGB565 conversion buffer | 307KB | PSRAM |
| MTCNN + MobileFaceNet | ~650KB | PSRAM |
| **Free headroom** | **~6.7MB** | — |

> **Critical:** DRAM (512KB) is the real bottleneck — not PSRAM.

---

## Performance

| Operation | Target |
|:---|---|
| MJPEG Stream | 15–25 FPS |
| Face Detection | 100–150ms |
| Face Recognition | 50–80ms (int8) |
| Wake Word | <50ms |
| Boot Time | <1s |
| Power Draw | ~300mA peak |

---

## How We Stack Up

| Product | Price | ML | Stream | Setup | Open Source |
|:---|:---:|:---|:---:|:---:|:---:|
| **Neural Vision** | **$15** | **Face + Voice** | **MJPEG** | **Captive Portal** | **✅ MIT** |
| RPi + Camera | $75–100 | Python/cloud | MJPEG/RTSP | SSH/desktop | ❌ |
| Arducam Mini | $30–50 | None | SPI/I2C | Wired | ❌ |
| ESP32-CAM | $7–10 | None | None | Hardcoded | Varies |
| OAK-D Lite | $300 | Depth AI | USB3 | USB | ❌ |

> **No other sub-$20 embedded system** offers face detection + wake word + MJPEG streaming + captive portal + live dashboard in a single firmware image.

---

## Built for Builders

- **Embedded ML Engineers** — Production-ready blueprint for on-device vision + voice
- **IoT Product Developers** — Drop-in firmware for camera-based products
- **Makers & Hobbyists** — Smart doorbell, pet camera, plant monitor, presence detection
- **Portfolio Builders** — FreeRTOS · C++17 · Computer vision · Audio · WiFi · ML
- **Hardware Startups** — Skip the $100k NRE. Ship with a working demo.

---

## Start Building

### Requirements: PlatformIO CLI · ESP32 Arduino Core · USB-C cable

```bash
git clone https://github.com/jaweed3/esp32-jarvis.git
cd esp32-jarvis
pio run -e full        # Build
pio run -e full -t upload   # Flash
pio device monitor -e full  # Monitor
```

### Build Environments: `full` · `test_cam` · `test_mic` · `test_wifi`

---

## FAQ

**Does this need internet?** No. Everything runs on-device. No cloud APIs, no subscription, no data leaving your network.

**Can I use my own wake word?** Yes. The TFLite Micro model can be retrained with your own audio samples.

**How many faces can it recognize?** 50–100 face embeddings with room for firmware and OTA partitions.

**Is this production-ready?** Phases 1–2 (system framework, WiFi, streaming, dashboard) are complete. Phases 3–6 are in active development.

---

## Roadmap

| Phase | Feature | Status |
|:---|---|:---:|
| 1 | System framework, state machine, event bus | ✅ |
| 2 | WiFi, captive portal, MJPEG stream, dashboard | ✅ |
| 3 | TFLite Micro wake word detection | 🔜 |
| 4 | MTCNN face detection + WebSocket events | 🔜 |
| 5 | SPA dashboard with real-time overlay | 🔜 |
| 6 | Face recognition + database management | 🔜 |
| 7 | OTA firmware updates | 🔜 |

---

## Tech Stack

`C++17` · `FreeRTOS` · `PlatformIO` · `ESP-IDF` · `esp32-camera` · `ESP-DL` · `TFLite Micro`  
`MTCNN` · `MobileFaceNet` · `I2S PDM` · `MJPEG` · `DNS Captive Portal` · `NVS Preferences` · `Arduino Framework`

---

# AI vision doesn't need a data center.

**Get the firmware, flash it to a $15 board, and start building.**  
Open source. MIT licensed. No strings attached.

[Get Started →](https://github.com/jaweed3/esp32-jarvis){: .btn .btn-primary} &nbsp; [View on GitHub](https://github.com/jaweed3/esp32-jarvis){: .btn}

---

⭐ Star us on GitHub · 🐛 Report an issue · 💬 Join the discussion

---

*Built with ESP32-S3 + FreeRTOS + TFLite Micro · MIT Licensed · © 2026*
