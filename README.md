# ESP32-S3 Neural Vision

Edge AI camera with **wake word detection** and **face recognition** running entirely on-device. Built on **Seeed Studio XIAO ESP32S3 Sense** with 8MB PSRAM, OV2640 camera, and digital MEMS microphone.

> Status: **Phase 2 Complete** — WiFi manager, captive portal, camera streaming, and state machine integrated.

---

## Hardware

| Component | Spec |
|---|---|
| MCU | ESP32-S3, Xtensa LX7 dual-core @ 240MHz |
| PSRAM | 8MB (OPI) |
| Flash | 8MB |
| Camera | OV2640 (1600×1200 max) |
| Mic | Digital MEMS (PDM, I2S) |
| Wireless | WiFi 2.4GHz + BLE 5.0 |
| Storage | MicroSD slot (up to 32GB) |
| Board | Seeed Studio XIAO ESP32S3 Sense |

---

## Architecture

### FreeRTOS Task Layout

```
Core 0 (PRO — Network):  WiFi stack, HTTP Server
Core 1 (APP — Processing): Audio capture, Camera pipeline, ML inference, State machine
```

Inter-task communication via **EventBus** (FreeRTOS Queue) with typed event messages.

### State Machine

```
                        ┌──────────────────┐
                        │      INIT        │  Hardware init, PSRAM alloc
                        └────────┬─────────┘
                                 │
                    Has saved WiFi credentials?
                         /               \
                       YES                NO
                        ↓                  ↓
                 ┌──────────┐       ┌───────────┐
                 │CONNECTING│       │  AP_MODE  │  Captive Portal @ 192.168.4.1
                 └────┬─────┘       └─────┬─────┘
                      │                   │ User sets up WiFi → saves to NVS → reboot
                 ┌────▼─────┐             │
                 │   IDLE   │◄────────────┘
                 └────┬─────┘  Online, wake word listening, stream optional
                      │
                 wake word detected
                      ↓
                 ┌──────────┐
                 │  ACTIVE  │  Camera + face detection active, 30s timeout → IDLE
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │  ERROR   │  Auto-recovery (3x retry → deep sleep)
                 └──────────┘
```

### Data Flow

```
PDM Mic ──→ I2S ──→ Ring Buffer (PSRAM, 3s) ──→ VAD ──→ Wake Word ML
                                                              │
OV2640 ──→ JPEG Buffer (DRAM) ──→ MJPEG HTTP Stream ──→ Browser Dashboard
                │
                └──→ [future] Face Detection ──→ WebSocket Events
```

### PSRAM Budget (8MB available)

| Component | Size | Location |
|---|---|---|
| Audio ring buffer (3s) | 96KB | PSRAM |
| Audio processing + MFCC | 40KB | PSRAM |
| TFLite tensor arena | 32KB | PSRAM |
| RGB565 conversion buffer | 307KB | PSRAM |
| Face detection (MTCNN) | 250KB | PSRAM |
| Face recognition (MobileFaceNet) | 400KB | PSRAM |
| Face DB + HTTP/WS buffers | 64KB | PSRAM |
| Camera frame buffers (2x) | ~100KB | DRAM |
| FreeRTOS task stacks | ~32KB | DRAM |
| **Total** | **~1.3MB** | — |
| **Headroom** | **~6.7MB** | — |

---

## Directory Structure

```
esp32/
├── platformio.ini              # Build config (4 environments)
├── README.md
│
├── src/
│   ├── main.cpp                # Entry point → SystemManager
│   ├── pins_config.h           # Camera pin definitions
│   │
│   ├── core/
│   │   ├── SystemManager.h     # Orchestrator: init sequence, main loop
│   │   ├── StateMachine.h      # FSM (INIT/AP/CONNECTING/IDLE/ACTIVE/ERROR)
│   │   └── EventBus.h          # RTOS queue pub/sub messaging
│   │
│   ├── memory/
│   │   └── MemoryManager.h     # PSRAM alloc/free + budget tracking
│   │
│   ├── wifi/
│   │   ├── WifiManager.h       # AP/STA mode, NVS credentials
│   │   └── CaptivePortal.h     # DNS server, WiFi setup UI
│   │
│   ├── audio/
│   │   └── AudioManager.h      # I2S PDM ring buffer + VAD
│   │
│   ├── vision/
│   │   └── CameraManager.h     # OV2640 camera control
│   │
│   ├── server/
│   │   └── HttpServer.h        # HTTP server + MJPEG stream
│   │
│   ├── storage/
│   │   └── ConfigManager.h     # NVS Preferences wrapper
│   │
│   ├── tests/                  # Standalone test modules
│   │   ├── test_cam.cpp        # Camera + WiFi + Stream
│   │   ├── test_mic.cpp        # Microphone recording
│   │   └── test_wifi.cpp       # WiFi manager + Captive portal
│   │
│   └── archive/                # Legacy files (for reference)
│
└── .pio/                       # PlatformIO build artifacts (gitignored)
```

---

## Quick Start

### Prerequisites

- [PlatformIO IDE](https://platformio.org/install) or CLI
- USB-C cable
- XIAO ESP32S3 Sense

### Build

```bash
# Full integrated firmware
pio run -e full

# Or test individual modules:
pio run -e test_cam     # Camera + WiFi + Stream
pio run -e test_mic     # Microphone recording
pio run -e test_wifi    # WiFi manager + Captive portal
```

### Flash & Monitor

```bash
# Flash & open serial monitor
pio run -e full -t upload
pio device monitor -e full

# Or for a specific test:
pio run -e test_cam -t upload
pio device monitor -e test_cam
```

### First-time Setup

1. Flash `full` or `test_wifi` firmware
2. ESP32 creates AP **"ESP32-S3-Setup"** (open network)
3. Connect phone/laptop to this AP
4. Browser auto-opens captive portal at **192.168.4.1**
5. Select your WiFi network, enter password, click **Connect**
6. Device reboots and connects to your WiFi
7. Open the dashboard at the IP shown in Serial Monitor

### Factory Reset

Visit `http://<device-ip>/api/factory-reset` or press **Factory Reset** button on the dashboard. Clears stored WiFi credentials and reboots into AP mode.

---

## API Reference

### HTTP Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard SPA with live status |
| `GET` | `/stream` | MJPEG camera stream (`multipart/x-mixed-replace`) |
| `GET` | `/capture` | Single JPEG photo |
| `GET` | `/api/status` | System status (JSON) |
| `GET` | `/api/config` | Current configuration (JSON) |
| `GET` | `/api/factory-reset` | Clear WiFi credentials + reboot |
| `POST` | `/api/system/reboot` | Reboot device |

### `/api/status` Response

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

### `/api/config` Response

```json
{
  "wifi_ssid": "MyNetwork",
  "face_threshold": 0.55,
  "wake_threshold": 0.70,
  "stream_enabled": true,
  "cam_resolution": 6
}
```

---

## Build Environments

| Environment | Contents | Use Case |
|---|---|---|
| `full` | All modules integrated | Production firmware |
| `test_cam` | Camera + WiFi + Stream only | Verify camera hardware & streaming |
| `test_mic` | AudioManager + serial dump | Verify microphone & PSRAM recording |
| `test_wifi` | WifiManager + CaptivePortal | Verify WiFi setup flow |

Each test environment is **completely independent** — flash and test one module without affecting others.

---

## Configuration

Configuration is stored in **NVS (Non-Volatile Storage)** via the `Preferences` library in the `"wifi"` and `"esp32sense"` namespaces.

| Key | Type | Default | Description |
|---|---|---|---|
| `wifi_ssid` | string | `""` | WiFi SSID |
| `wifi_pass` | string | `""` | WiFi password |
| `face_thresh` | float | `0.55` | Face recognition threshold |
| `wake_thresh` | float | `0.70` | Wake word confidence threshold |
| `stream_enabled` | bool | `true` | Auto-start stream |
| `cam_res` | int | `6` (HVGA) | Camera resolution (framesize_t) |

---

## Camera Pinout

From `src/pins_config.h` — configured for XIAO ESP32S3 Sense expansion board:

| Signal | GPIO |
|---|---|
| XCLK | 10 |
| PCLK | 13 |
| VSYNC | 38 |
| HREF | 47 |
| SIOD | 40 |
| SIOC | 39 |
| Y2-Y9 | 15,17,18,16,14,12,11,48 |
| PWDN | -1 (unused) |
| RESET | -1 (unused) |

Microphone: I2S DOUT=42, CLK=41 (PDM_MONO_MODE)

---

## Roadmap

- [x] **Phase 1** — Clean architecture, all hardware modules
- [x] **Phase 2** — WiFi manager, captive portal, state machine
- [ ] **Phase 3** — Audio pipeline + wake word detection (TFLite Micro)
- [ ] **Phase 4** — Face detection (ESP-DL MTCNN)
- [ ] **Phase 5** — Web dashboard (full SPA with WebSocket)
- [ ] **Phase 6** — Face recognition + enrollment database
- [ ] **Phase 7** — OTA updates + production polish

---

## License

MIT
