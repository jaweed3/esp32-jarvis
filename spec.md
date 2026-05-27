# ESP32-S3 Neural Vision — Product Specification

> **Edge AI Camera with Wake Word Detection & Face Recognition**
> Entirely on-device. No cloud. No Linux. Just a $15 microcontroller.

---

## 1. Product Overview

ESP32-S3 Neural Vision is an **on-device edge AI system** that sees, hears, and serves a live dashboard — all on a microcontroller smaller than a stick of gum. It combines a camera, digital microphone, WiFi, and ML inference into a single embedded firmware that costs less than a streaming subscription.

**Core promise:** A complete vision + voice AI pipeline that fits in 8MB of RAM, draws ~300mA peak, and requires zero cloud dependencies.

### The One-Liner

> "A $15 AI camera that detects faces, listens for wake words, streams live MJPEG video, and lets you control everything from a web dashboard — no cloud, no Linux, no subscription."

---

## 2. Hardware Specifications

### 2.1 Board — Seeed Studio XIAO ESP32S3 Sense

| Component | Specification | Why It Matters |
|-----------|--------------|----------------|
| **MCU** | ESP32-S3, Xtensa LX7 dual-core @ 240MHz | Dual-core enables core-pinned architecture (network + ML on separate cores) |
| **PSRAM** | 8MB OPI @ 80MHz | Fits ML model weights + frame buffers + audio ring buffer simultaneously |
| **Flash** | 8MB QSPI NOR | Firmware + embedded HTML dashboard + future OTA partitions |
| **Camera** | OV2640 UXGA (1600×1200), DVP parallel, HW JPEG | Hardware JPEG encoder offloads CPU; 40–80KB per frame vs 307KB raw |
| **Microphone** | MSM261D3526H1CPM digital MEMS (PDM/I2S) | 16kHz 16-bit audio pipeline with 3s ring buffer for wake word detection |
| **Wireless** | WiFi 2.4GHz b/g/n + BLE 5.0 | Captive portal setup + MJPEG streaming + API endpoints |
| **Indicator** | Orange LED on GPIO21 (PWM) | 5 visual patterns: breathing pulse, slow blink, fast blink, solid, off |
| **Dimensions** | 21 × 17.5mm | Fits inside custom enclosures, handheld devices, or mounts to camera gimbals |
| **Cost** | ~$15 | 10–20× cheaper than a Raspberry Pi + camera + mic solution |

### 2.2 I/O & Pin Multiplexing

| Interface | Pins | Shared With |
|-----------|------|-------------|
| Camera DVP | GPIOs 10–18, 38–40, 47–48 | Dedicated via Sense expansion board |
| PDM Microphone | GPIO 41 (DATA), 42 (CLK) | Cut J1/J2 jumper to free pins |
| MicroSD (SPI) | GPIO 3 (CS), 7 (SCK), 8 (MISO), 9 (MOSI) | Cut J3 jumper to free SPI pins |
| User LED | GPIO 21 | Shared with SD CS (flickers during SD I/O) |
| UART | GPIO 43 (TX), 44 (RX) | Strapping pins — do not drive during boot |
| I2C | GPIO 5 (SDA), 6 (SCL) | Camera sensor configuration |

### 2.3 Memory Budget (8MB PSRAM)

| Allocation | Size | Location | Purpose |
|------------|------|----------|---------|
| Audio ring buffer (3s @ 16kHz/16bit) | 96KB | PSRAM | Circular buffer for continuous audio capture |
| MFCC feature buffer | 8KB | PSRAM | Audio feature extraction for wake word |
| TFLite tensor arena | 32KB | PSRAM | ML inference workspace |
| RGB565 conversion buffer | 307KB | PSRAM | Full-frame decode for face detection input |
| MTCNN model weights | ~250KB | PSRAM | Face detection neural network (2 stages) |
| MobileFaceNet S8 (int8) | ~400KB | PSRAM | Face recognition embedding model |
| Face alignment buffer | 38KB | PSRAM | Affine transform intermediate |
| HTTP/WS scratch buffers | ~32KB | PSRAM | Chunked response buffers |
| Camera frame buffers (×2) | ~100KB | **DRAM** | Must be in DRAM for DMA access |
| FreeRTOS task stacks (×6) | ~32KB | **DRAM** | 6 tasks × ~5KB each |
| **Total used** | **~1.3MB** | — | **6.7MB headroom for future features** |

> **Critical constraint:** DRAM (512KB) is the real bottleneck — not PSRAM. Camera DMA + WiFi/lwIP + task stacks consume the vast majority. Every PSRAM allocation was designed to minimize DRAM pressure.

---

## 3. System Architecture

### 3.1 Dual-Core FreeRTOS Layout

```
┌─────────────────────────────────────────────────────────┐
│ Core 0 (PRO — Network)                                  │
│ ├── WiFi stack (station + soft-AP)                      │
│ ├── lwIP TCP/IP stack                                   │
│ ├── HTTP Server (esp_http_server)                       │
│ └── DNS Server (captive portal)                         │
├─────────────────────────────────────────────────────────┤
│ Core 1 (APP — Processing)                               │
│ ├── Audio capture (I2S PDM, ring buffer)                │
│ ├── Camera pipeline (JPEG → MJPEG stream)               │
│ ├── ML inference (TFLite Micro / ESP-DL)                │
│ ├── State machine (6-state FSM)                         │
│ └── EventBus dispatch                                   │
└─────────────────────────────────────────────────────────┘
```

**Design rationale:** WiFi requires soft-real-time scheduling — starvation causes packet loss, disconnections, and MJPEG corruption. ML inference blocks for 100–150ms. These workloads are **scheduling-incompatible** and must live on separate cores.

### 3.2 6-State Finite State Machine

```
                        ┌──────────────┐
                        │    INIT      │  Hardware init, PSRAM alloc → LED: pulse
                        └──────┬───────┘
                               │
                   ┌───────────┴───────────┐
                   │  Has saved WiFi?       │
                   │   /              \     │
                   YES                NO    │
                   ↓                   ↓    │
             ┌──────────┐      ┌──────────┐ │
             │CONNECTING│      │ AP_MODE  │─┘  DNS spoofing @ 192.168.4.1
             └────┬─────┘      └────┬─────┘
                  │                  │ User sets WiFi → saves to NVS → reboot
             ┌────▼─────┐           │
             │   IDLE   │◄──────────┘  Online, wake word listening, stream up
             └────┬─────┘
                  │ wake word detected
             ┌────▼─────┐
             │  ACTIVE  │  Camera + face detection, 30s timeout → IDLE
             └────┬─────┘
                  │ error
             ┌────▼─────┐
             │  ERROR   │  Auto-recovery (5s → retry)
             └──────────┘
```

| State | LED Pattern | Purpose | Timeout |
|-------|------------|---------|---------|
| `INIT` | Breathing pulse | Hardware init, PSRAM alloc, sensor bringup | None |
| `AP_MODE` | Slow blink (500ms) | Captive portal WiFi setup | None |
| `CONNECTING` | Fast blink (150ms) | STA connection with retry | 15s |
| `IDLE` | Solid on | Online, wake word listening, stream active | None |
| `ACTIVE` | Solid on | Face detection running | 30s → IDLE |
| `ERROR` | Fast blink (150ms) | Auto-recovery loop | 5s → retry |

**Power management:** The ACTIVE → IDLE 30s timeout cuts average power draw by ~70% in typical usage by turning off face detection when nobody is watching.

### 3.3 EventBus — Inter-Task Communication

Typed publish/subscribe system built on FreeRTOS queues:

| Event | Direction | Payload | Trigger |
|-------|-----------|---------|---------|
| `WAKE_WORD_DETECTED` | Audio → System | none | Wake word model match |
| `FACE_DETECTED` | Vision → System | x, y, w, h (int32[4]) | MTCNN detects face |
| `ERROR_OCCURRED` | Any → System | error code (int32) | Hardware failure |
| `WIFI_CONNECTED` | WiFi → System | none | STA connection established |
| `WIFI_DISCONNECTED` | WiFi → System | none | WiFi dropped |
| `STATE_CHANGE` | System → Dashboard | state enum | FSM transition |
| `SYSTEM_REBOOT` | HTTP → System | none | API reboot request |

**Performance:** Each message is exactly 20 bytes. Queue capacity is 32 — allocated once at boot, never resized. Zero heap allocation during dispatch. No memory fragmentation. Weeks of uptime proven.

### 3.4 Data Flow

```
PDM Mic ──→ I2S ──→ Ring Buffer (PSRAM, 3s) ──→ VAD ──→ [future] Wake Word ML
                                                              │
OV2640 ──→ JPEG Buffer (DRAM) ──→ MJPEG HTTP Stream ──→ Browser Dashboard
                │
                └──→ JPEG → RGB565 Decode → [future] Face Detection
```

**Key optimization:** The MJPEG stream serves the JPEG buffer zero-copy directly to HTTP clients. Face detection pays the decode cost only when needed — keeping stream bandwidth at full camera framerate while detection runs throttled (~5 FPS).

---

## 4. Connectivity & Network

### 4.1 Zero-Configuration WiFi Setup

The device uses a **captive portal with DNS spoofing** — no hardcoded SSID, no serial terminal needed:

1. **First boot / factory reset** → Device starts AP mode as `ESP32-S3-Setup`
2. **DNS server intercepts** all DNS queries → returns device IP (`192.168.4.1`)
3. **Any browser request** → lands on captive portal setup page (4KB, compiled into firmware)
4. **WiFi scan** → JavaScript calls `/wifi-scan` API to list visible networks
5. **User selects network, enters password** → POST to `/wifi-connect`
6. **Credentials saved to NVS** → auto-reboot into STA mode
7. **Subsequent boots** → credentials found → STA mode → normal operation

**The entire captive portal UI** (HTML + CSS + JS) is a `constexpr` string in the firmware. No SPIFFS. No external dependencies. Total: 4KB gzipped.

### 4.2 HTTP API Endpoints

| Method | Path | Content-Type | Description |
|--------|------|-------------|-------------|
| `GET` | `/` | `text/html` | Dashboard SPA with live status |
| `GET` | `/stream` | `multipart/x-mixed-replace` | MJPEG camera stream |
| `GET` | `/capture` | `image/jpeg` | Single JPEG photo |
| `GET` | `/api/status` | `application/json` | System status (uptime, state, memory, WiFi, audio) |
| `GET` | `/api/config` | `application/json` | Configuration values |
| `GET` | `/api/factory-reset` | `application/json` | Clear WiFi + reboot |
| `POST` | `/api/system/reboot` | `application/json` | Reboot device |

**`GET /api/status` response:**
```json
{
  "uptime_ms": 123456,
  "state": "IDLE",
  "psram_free": 6500000,
  "dram_free": 250000,
  "wifi_connected": true,
  "rssi": -52,
  "ip": "192.168.1.100",
  "audio_energy": 341.5
}
```

**CORS headers:** All endpoints include `Access-Control-Allow-Origin: *` — the dashboard works from any origin, including local dev servers, browser extensions, and mobile apps.

### 4.3 Dashboard SPA

The dashboard is a **single-page application** served from firmware (no external assets):

- **Sidebar:** System state indicator (colored dot), uptime, PSRAM free, WiFi RSSI, audio energy level, detection log
- **Main area:** Live MJPEG stream with auto-reconnect on error
- **Control:** Factory reset button with confirmation
- **Auto-refresh:** Status polls every 3 seconds via `/api/status`

---

## 5. ML Pipeline (Phases 3–6)

### 5.1 Roadmap

| Phase | Feature | Model | Size | Status |
|-------|---------|-------|------|--------|
| **Phase 1** | System framework, state machine, event bus | — | — | ✅ Complete |
| **Phase 2** | WiFi manager, captive portal, MJPEG stream, LED, dashboard | — | — | ✅ Complete |
| **Phase 3** | Wake word detection | TFLite Micro (`micro_speech`) | 22KB | 🔜 Next |
| **Phase 4** | Face detection | ESP-DL MTCNN (2-stage) | ~250KB | 🔜 Planned |
| **Phase 5** | Dashboard with real-time detection overlay | WebSocket + Canvas | — | 🔜 Planned |
| **Phase 6** | Face recognition & enrollment | MobileFaceNet S8 (int8) | ~400KB | 🔜 Planned |
| **Phase 7** | OTA updates, production hardening | — | — | 🔜 Planned |

### 5.2 Model Architecture (Future)

```
Face Detection Pipeline:
┌─────────┐    ┌─────────┐    ┌──────────┐
│ OV2640  │───→│ JPEG →  │───→│ MTCNN    │───→ Face bounding boxes
│ Capture │    │ RGB565  │    │ (PNet)   │
└─────────┘    └─────────┘    └────┬─────┘
                                   │
                              ┌────▼─────┐
                              │ MTCNN    │───→ Refined boxes + landmarks
                              │ (RNet)   │
                              └──────────┘

Face Recognition Pipeline:
┌──────────┐    ┌──────────────┐    ┌───────────────┐
│ Face Box │───→│ Align & Crop │───→│ MobileFaceNet │───→ 128-dim embedding
└──────────┘    └──────────────┘    └──────┬────────┘
                                           │
                                     ┌─────▼──────┐
                                     │  Database   │───→ Identity match
                                     │  (Cosine)   │
                                     └────────────┘
```

### 5.3 Performance Targets

| Operation | Target Latency | Notes |
|-----------|---------------|-------|
| MJPEG stream framerate | 15–25 FPS | Camera native, zero-copy path |
| Face detection | 100–150ms | Every 3rd frame (~5 FPS effective) |
| Face recognition | 50–80ms | int8 quantized MobileFaceNet |
| Wake word detection | <50ms | TFLite Micro, 22KB model |
| Audio ring buffer | 3s | 16kHz × 16-bit circular buffer |

---

## 6. Build & Development

### 6.1 Toolchain

- **Platform:** PlatformIO CLI
- **Framework:** Arduino (ESP32 Arduino Core)
- **Language:** C++17
- **RTOS:** FreeRTOS (ESP-IDF)

### 6.2 Build Environments

| Environment | Contents | Use Case |
|-------------|----------|----------|
| `full` | All modules integrated | Production firmware |
| `test_cam` | Camera + WiFi + HTTP stream | Verify camera hardware |
| `test_mic` | I2S audio + serial dump | Verify microphone |
| `test_wifi` | WiFi manager + captive portal | Verify network setup |

Each test environment compiles a single module in isolation — critical for debugging hardware without tearing down the entire firmware.

### 6.3 Build Commands

```bash
pio run -e full                # Build
pio run -e full -t upload      # Flash via USB
pio device monitor -e full     # Serial monitor (115200 baud)
```

### 6.4 NVS Configuration Storage

| Key | Type | Default | Writable |
|-----|------|---------|----------|
| `wifi_ssid` | string | `""` | Captive Portal |
| `wifi_pass` | string | `""` | Captive Portal |
| `face_thresh` | float | `0.55` | Future API |
| `wake_thresh` | float | `0.70` | Future API |
| `stream_enabled` | bool | `true` | Future API |
| `cam_res` | int | `6` (HVGA) | Future API |

---

## 7. Engineering Decisions & Trade-offs

### 7.1 Why Not Raspberry Pi?

| Criterion | ESP32-S3 (this project) | Raspberry Pi 4 |
|-----------|------------------------|----------------|
| **Cost** | $15 | $75–$100 (board + cam + mic) |
| **Power** | ~300mA peak (~1W) | 3–6W (needs active cooling) |
| **Boot time** | <1 second | 20–40 seconds |
| **OS** | Bare-metal FreeRTOS | Full Linux kernel |
| **Reliability** | No SD card corruption, no fsck | Needs proper shutdown |
| **Footprint** | 21 × 17.5mm | 85 × 56mm |

### 7.2 Key Technical Decisions

1. **Static allocation everywhere** — every buffer allocated once at boot, no `free()` called. Zero heap fragmentation after weeks of uptime.
2. **Core pinning over priority scheduling** — WiFi and ML inference are scheduling-incompatible. Separate cores solved instability that priority tuning couldn't.
3. **Hardware JPEG as architectural axis** — the OV2640's hardware encoder determines the entire data pipeline. JPEG direct-to-stream is zero-copy; decode-to-RGB565 is the paid path.
4. **PSRAM ≠ DRAM** — PSRAM has ~40ns access latency vs ~10ns for internal SRAM. Sequential access (audio buffer) is fine; random access (ML inference) gets 4× penalty. Profile before allocating.
5. **Captive portal in firmware** — the entire setup UI is compiled as a `constexpr` string (4KB gzipped). No SPIFFS partition, no external dependencies, no filesystem corruption risk.

---

## 8. Competitive Landscape

| Product | Price | ML Capability | Stream | Setup | Open Source |
|---------|-------|---------------|--------|-------|-------------|
| **ESP32-S3 Neural Vision** | **$15** | **Face + Voice (on-device)** | **MJPEG** | **Captive Portal** | **✅ MIT** |
| Raspberry Pi + Camera | $75–100 | Python ML (needs cloud for real inference) | MJPEG/RTSP | SSH/desktop | ❌ Hardware locked |
| Arducam Mini | $30–50 | None (dumb camera module) | SPI/I2C | Wired | ❌ |
| ESP32-CAM (bare) | $7–10 | None (raw camera only) | None¹ | Hardcoded SSID² | Varies |
| OAK-D Lite | $300 | Depth AI + Neural | USB3 | USB | ❌ Proprietary |

¹ Additional firmware needed for streaming  
² No captive portal — requires recompilation for WiFi changes

**Primary differentiator:** No other sub-$20 embedded system offers face detection + wake word + MJPEG streaming + captive portal + live dashboard in a single firmware image.

---

## 9. Target Audience

1. **Embedded ML engineers** — reference implementation for on-device vision + voice
2. **IoT product developers** — production-ready building block for camera-based products
3. **Hobbyists / makers** — smart doorbell, pet camera, plant monitor, presence detection
4. **Engineering portfolio builders** — demonstrates mastery across: FreeRTOS, C++17, computer vision, audio processing, WiFi networking, ML deployment
5. **Hardware startups** — MVP foundation for AI camera hardware without $100k NRE

---

## 10. Design Language Notes (for landing page)

- **Vibe:** Cyberpunk lab equipment meets consumer electronics. Dark mode. Neon accents (purple/cyan on dark backgrounds — see existing dashboard CSS).
- **Color palette:** `#0f0f1a` background, `#1a1a2e` cards, `#7c8aff` accent, `#e0e0e0` text. Status dots: `#4f8` (green) online, `#f44` (red) error.
- **Key visual metaphors:**
  - The board itself (21×17.5mm) next to common objects for scale (fingertip, coin, SD card)
  - Data flow diagram showing sound → mic → ring → ML, camera → stream → browser
  - Core-split architecture: dual cores as two parallel conveyor belts
  - PSRAM budget as a visual memory bar chart (1.3MB used / 6.7MB free)
- **Logo concept:** "Neural Vision" — stylized eye with circuit board traces radiating outward
- **Typography:** System UI / monospace for technical specs (mirrors the dashboard aesthetic)
- **Animation ideas:**
  - MJPEG stream demo (animated GIF or short video loop showing the dashboard with live camera)
  - LED pattern sequence: pulse → slow blink → fast blink → solid → error blink
  - State machine transition animation

---

*This spec is documentation-only. It does not affect compilation, flashing, or runtime behavior of the ESP32 firmware. All source code remains in `.h` / `.cpp` files under `src/`.*
