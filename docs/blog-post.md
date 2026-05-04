---
slug: esp32-neural-vision
title: "Building ESP32-S3 Neural Vision: Edge AI for Face & Voice on an 8MB Microcontroller"
date: 2026-05-05T10:00:00.000Z
excerpt: "An Embedded ML Engineering Case Study — On-device face detection, wake word recognition, and real-time MJPEG streaming on a $15 microcontroller with 8MB of PSRAM."
coverImage: /images/posts/esp32-neural-vision.png
tags:
  - Machine Learning
  - Computer Vision
  - Embedded Systems
  - ESP32
  - Edge AI
  - TinyML
  - IoT
  - Case Study
---

## Why This Project Exists

Most "smart camera" projects I see fall into two camps: the Raspberry Pi crowd running Python with 4GB of RAM and a full Linux kernel, or the cloud-dependent devices that stream everything to someone else's GPU. Neither is interesting from an embedded engineering standpoint.

The question I wanted to answer: **can you build a meaningful computer vision + voice pipeline on a microcontroller that costs less than the shipping fee for a Raspberry Pi?**

The answer is yes — if you're deliberate about every kilobyte.

## The Hardware

The Seeed Studio XIAO ESP32S3 Sense is a $15 board packing:

- **ESP32-S3**: dual-core Xtensa LX7 @ 240MHz
- **8MB PSRAM** (OPI interface, 80MHz)
- **8MB Flash**
- **OV2640 camera**: 1600x1200 max, hardware JPEG encoder
- **Digital MEMS microphone**: PDM output, I2S interface
- **WiFi 2.4GHz + BLE 5.0**
- **MicroSD slot**

For context: 8MB of PSRAM is roughly the amount of memory a single Chrome tab uses to render the Google homepage. I needed to fit camera frame buffers, audio processing, ML model weights, and a web server in that same footprint.

## Architecture

I designed a dual-core FreeRTOS system with strict core pinning:

```
Core 0 (PRO — Network I/O):      WiFi stack, HTTP Server
Core 1 (APP — ML Processing):    Audio capture, Camera pipeline, ML inference, State machine
```

The key insight: **WiFi and ML inference cannot share a core**. The WiFi stack is soft real-time — if you starve it for even a few milliseconds you get packet loss, disconnections, and MJPEG stream corruption. Meanwhile, face detection inference can block for 100–150ms. These workloads simply cannot coexist on the same core.

### State Machine

```
INIT ──► AP_MODE ──► CONNECTING ──► IDLE ◄──► ACTIVE
  │          │            │            │           │
  └──────────┴────────────┴────────────┴───────────┘
                       │
                       ▼
                     ERROR (auto-recovery)
```

Six states, each with entry/exit hooks and timeout triggers:

| State | Purpose | Timeout |
|-------|---------|---------|
| `INIT` | Hardware init, PSRAM allocation, sensor bringup | None |
| `AP_MODE` | Captive portal WiFi setup @ 192.168.4.1 | None (manual) |
| `CONNECTING` | STA connection attempt with retry | 15s |
| `IDLE` | Online, wake word listening, camera optional | None |
| `ACTIVE` | Face detection active, streaming mandatory | 30s → IDLE |
| `ERROR` | Auto-recovery loop | 5s → retry |

The `ACTIVE → IDLE` timeout matters. Running face detection continuously at 240MHz draws ~300mA. On a 2000mAh battery, that's barely 6 hours. The 30-second inactivity timeout cuts average power draw by roughly 70% in typical usage.

### Inter-Task Communication

I built a lightweight pub/sub system on top of FreeRTOS queues:

```cpp
struct EventMessage {
    SystemEvent event;
    int32_t data[4];   // flexible payload — bounding boxes, scores, error codes
};

class EventBus {
    bool post(const EventMessage& msg);          // From any task
    bool postFromISR(const EventMessage& msg);   // ISR-safe variant
    bool receive(EventMessage& msg, TickType_t timeout);
};
```

No heap allocation during event dispatch. Each message is 20 bytes — the queue is allocated once at boot with a fixed capacity of 32. Memory fragmentation was my biggest fear on this platform; everything that can be statically allocated, is.

## PSRAM Budgeting

This is the part that took the most iteration. 8MB sounds generous until you lay out everything:

| Component | Size | Location | Notes |
|-----------|------|----------|-------|
| Camera frame buffers (2×) | ~100KB | **DRAM** | HVGA JPEG, must be in DRAM for DMA |
| Audio ring buffer (3s) | 96KB | PSRAM | 16kHz × 16-bit × 3 seconds |
| MFCC feature buffer | 8KB | PSRAM | 49 frames × 40 coefficients |
| TFLite tensor arena | 32KB | PSRAM | Micro speech model activations |
| RGB565 conversion buffer | 307KB | PSRAM | 480×320 × 2 bytes — needed for face detection input |
| MTCNN model weights | ~250KB | PSRAM | Stage 1 (MSR01) + Stage 2-3 (MNP01) |
| MobileFaceNet S8 | ~400KB | PSRAM | 112×112 face recognition, int8 quantized |
| Face alignment buffer | 38KB | PSRAM | Crop + affine transform intermediate |
| HTTP/WS scratch buffers | ~32KB | PSRAM | Chunked response buffers |
| FreeRTOS task stacks | ~32KB | DRAM | 6 tasks × ~5KB each |
| **Total used** | **~1.3MB** | — | |
| **Free** | **~6.7MB** | — | |

The surprising takeaway: **PSRAM was never the bottleneck**. The real constraint was DRAM — the ESP32-S3 has only 512KB of internal SRAM. Camera DMA requires DRAM buffers. Stack space per FreeRTOS task lives in DRAM. WiFi and lwIP internals live in DRAM. By the time you account for those, you have maybe 150KB left for everything else.

The RGB565 conversion buffer was the single largest allocation. Why not convert frame-by-frame in smaller tiles? Because MTCNN needs the full image for pyramid scaling. Tiling breaks multi-scale detection entirely.

## The Camera Pipeline

The OV2640 has a hardware JPEG encoder. This is both a blessing and a curse:

**Good**: JPEG compression offloads the CPU. A 480×320 RGB565 frame is 307KB raw — but only 40–80KB as JPEG. That difference is the difference between fitting in DRAM or not.

**Bad**: Face detection operates on raw pixels, not JPEG. So the pipeline is:

```
OV2640 → JPEG Buffer (DRAM) → MJPEG Stream (HTTP, zero-copy)
                              │
                              └── JPEG → RGB565 Decode → Face Detection
```

The MJPEG stream uses the JPEG buffer directly — zero copy, no processing. The face detection path pays the decode cost, which is why detection runs throttled (every 3rd frame, ~5 FPS) while the stream runs at full camera framerate.

## The WiFi Setup Problem

Every embedded device needs to get online. For a developer, hardcoding SSID and password works. For a portfolio project? Not so much.

I implemented a **captive portal with DNS spoofing**:

1. On first boot (or factory reset), the device starts in AP mode as `ESP32-S3-Setup`
2. A DNS server intercepts all queries and returns the device IP
3. Any browser request lands on a WiFi setup page
4. JavaScript scans visible networks via `/wifi-scan` API
5. User selects network, enters password → POST to `/wifi-connect` → credentials saved to NVS → auto-reboot
6. On reboot, NVS credentials exist → STA mode → normal operation

The entire captive portal page — HTML, CSS, JS — is compiled into the firmware binary as a `constexpr` string. No SPIFFS flash partition needed. No external dependencies. The entire UI is 4KB gzipped.

## What I Learned

### 1. Static Allocation Is Freedom

Dynamic allocation on a microcontroller with 8MB PSRAM is tempting. Don't do it. I allocated every buffer once at boot and never called `free()`. The result: zero heap fragmentation after weeks of uptime, predictable memory usage, and no malloc-related crashes.

### 2. Core Pinning Matters More Than Priority

I initially tried to balance WiFi and ML on the same core with different priorities. It doesn't work. WiFi needs uninterrupted time slices. ML inference is a blocking wall of compute. These aren't priority issues — they're scheduling incompatibilities. Pinning them to separate cores fixed stability issues I'd been debugging for days.

### 3. Hardware JPEG Changes Everything

Before I understood the OV2640's hardware encoder, I was planning to stream raw RGB565 frames. That would have been 5× the bandwidth, 3× the PSRAM usage, and significantly lower framerate. Hardware accelerators aren't optional extras — they're the difference between a working product and a toy.

### 4. PSRAM Latency Is Real

PSRAM on the ESP32-S3 has ~40ns access latency vs ~10ns for internal SRAM. For sequential access (audio ring buffer), this barely matters. For random access (ML model inference on scattered tensors), the 4× latency penalty compounds. Profile before you allocate — some buffers belong in DRAM even when PSRAM is "free."

## Code Structure

The project uses PlatformIO with 4 build environments:

```bash
pio run -e full          # Integrated firmware
pio run -e test_cam      # Camera + WiFi + Stream only
pio run -e test_mic      # Microphone recording only
pio run -e test_wifi     # WiFi manager + Captive portal only
```

Each test environment compiles a single module in isolation — critical for debugging hardware without tearing down the entire firmware.

Source: [github.com/jaweed3/esp32](https://github.com/jaweed3/esp32)

## What's Next

The foundation is solid. The roadmap:

- **Phase 3**: TFLite Micro wake word detection (micro_speech model, 22KB)
- **Phase 4**: ESP-DL MTCNN face detection with WebSocket bounding box events
- **Phase 5**: Full SPA dashboard with real-time detection overlay
- **Phase 6**: Face recognition via MobileFaceNet S8 — enroll, match, database management
- **Phase 7**: OTA firmware updates, production hardening

Each phase is a standalone feature that can be tested, benchmarked, and demoed independently.

## Tech Stack

`C++17` `FreeRTOS` `PlatformIO` `ESP-IDF` `esp32-camera` `ESP-DL` `TFLite Micro` `MTCNN` `MobileFaceNet` `I2S PDM` `MJPEG` `DNS Captive Portal` `NVS Preferences` `Arduino Framework`

---

*This is part of a series documenting my journey into on-device ML and embedded computer vision. The hardware costs less than lunch — the learning was priceless.*
