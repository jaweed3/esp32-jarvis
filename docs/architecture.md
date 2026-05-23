# Architecture

## System Overview

```
USB-C ──→ ESP32-S3 ──→ OV2640 Camera (DVP)
                │
                ├──→ PDM Mic (I2S GPIO 41-42)
                ├──→ Orange LED (GPIO21 PWM)
                ├──→ MicroSD (SPI GPIO 3,7-9)
                └──→ WiFi AP/STA ──→ HTTP Server (port 80)
```

## FreeRTOS Task Layout

```
Core 0 (PRO — Network):  WiFi stack, HTTP Server
Core 1 (APP — Processing): Audio capture, Camera pipeline, ML inference, State machine
```

Inter-task communication via **EventBus** (FreeRTOS Queue) with typed event messages.

## State Machine

```
                        ┌──────────────┐
                        │    INIT      │  Hardware init, PSRAM alloc → LED: pulse
                        └──────┬───────┘
                               │
                   Has saved WiFi?
                       /          \
                     YES           NO
                      ↓             ↓
               ┌──────────┐  ┌──────────┐
               │CONNECTING│  │ AP_MODE  │  Captive Portal @ 192.168.4.1
               └────┬─────┘  └────┬─────┘
                    │             │
               ┌────▼─────┐       │  User sets WiFi → saves to NVS → reboot
               │   IDLE   │◄──────┘  Online, wake word listening, stream
               └────┬─────┘
                    │ wake word detected
               ┌────▼─────┐
               │  ACTIVE  │  Camera + face detection, 30s timeout → IDLE
               └────┬─────┘
                    │
               ┌────▼─────┐
               │  ERROR   │  Auto-recovery (5s → retry)
               └──────────┘
```

## Data Flow

```
PDM Mic ──→ I2S ──→ Ring Buffer (PSRAM, 3s) ──→ VAD ──→ Wake Word ML
                                                              │
OV2640 ──→ JPEG Buffer (DRAM) ──→ MJPEG HTTP Stream ──→ Browser Dashboard
                │
                └──→ [future] Face Detection ──→ WebSocket Events
```

## LED Indicator Reference

The onboard orange LED (GPIO21, active HIGH) indicates state via PWM patterns:

| State | Pattern | Meaning |
|-------|---------|---------|
| INIT | Breathing pulse | Initializing hardware |
| AP_MODE | Slow blink (500ms) | WiFi AP + captive portal |
| CONNECTING | Fast blink (150ms) | Connecting to WiFi |
| IDLE | Solid on | Online, ready |
| ACTIVE | Solid on | Wake word triggered, face detection |
| ERROR | Fast blink (150ms) | Error, auto-recovery in 5s |

## PSRAM Budget (8MB)

| Component | Size | Location |
|---|---|---|
| Audio ring buffer (3s @ 16kHz/16bit) | 96KB | PSRAM |
| Audio processing + MFCC | 40KB | PSRAM |
| TFLite tensor arena | 32KB | PSRAM |
| RGB565 conversion buffer | 307KB | PSRAM |
| Face detection + recognition | 650KB | PSRAM |
| Camera frame buffers (2x) | ~100KB | DRAM |
| FreeRTOS task stacks | ~32KB | DRAM |
| **Headroom** | **~6.7MB** | — |

## Directory Structure

```
esp32/
├── platformio.ini           # Build config (4 environments)
├── wiring_diagram.png       # Wiring diagram
├── README.md
├── docs/
│   ├── architecture.md      # This file
│   ├── api.md               # HTTP API reference
│   ├── pinout.md            # GPIO pinout tables
│   ├── build.md             # Build environments & config
│   ├── troubleshooting.md   # Common issues & fixes
│   ├── demo.gif             # Boot demonstration
│   ├── blog-post.md         # Project blog post
│   ├── wiring.puml          # Wiring diagram (PlantUML source)
│   └── pinout.puml          # Pinout diagram (PlantUML source)
├── src/
│   ├── main.cpp             # Entry point → SystemManager
│   ├── pins_config.h        # GPIO pin definitions
│   ├── core/
│   │   ├── SystemManager.h  # Orchestrator: init, main loop
│   │   ├── StateMachine.h   # FSM (6 states)
│   │   ├── EventBus.h       # FreeRTOS queue pub/sub
│   │   └── LedIndicator.h   # GPIO21 PWM patterns
│   ├── memory/MemoryManager.h
│   ├── wifi/WifiManager.h
│   ├── wifi/CaptivePortal.h
│   ├── audio/AudioManager.h
│   ├── vision/CameraManager.h
│   ├── server/HttpServer.h
│   ├── storage/ConfigManager.h
│   └── tests/               # Standalone test modules
└── .pio/                    # Build artifacts (gitignored)
```

## EventBus Messages

| Event | Direction | Payload |
|---|---|---|
| `WAKE_WORD_DETECTED` | Audio → System | none |
| `FACE_DETECTED` | Vision → System | x, y, w, h (int32[4]) |
| `ERROR_OCCURRED` | Any → System | error code (int32) |
| `WIFI_CONNECTED` | WiFi → System | none |
| `WIFI_DISCONNECTED` | WiFi → System | none |
| `STATE_CHANGE` | System → Dashboard | state enum |
| `SYSTEM_REBOOT` | HTTP → System | none |
