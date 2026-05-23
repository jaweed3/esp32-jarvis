# Build Guide

## Prerequisites

- [PlatformIO](https://platformio.org/install) CLI (`brew install platformio` or `pip install platformio`)
- USB-C cable
- Seeed Studio XIAO ESP32S3 Sense

## Build

```bash
# Full integrated firmware
pio run -e full

# Test individual modules:
pio run -e test_cam     # Camera + WiFi + Stream
pio run -e test_mic     # Microphone recording
pio run -e test_wifi    # WiFi manager + Captive portal
```

## Flash

```bash
pio run -e full -t upload
```

If auto-detection picks the wrong serial port, set it explicitly in `platformio.ini`:

```ini
upload_port = /dev/cu.usbmodem31301
```

For verbose flash output (see exact esptool commands):

```bash
pio run -e full -t upload --verbose
```

## Serial Monitor

```bash
pio device monitor -e full
```

Baud rate: `115200` (set via `monitor_speed` in `platformio.ini`).

Exception decoder is enabled via `monitor_filters = esp32_exception_decoder, time`.

## First-Time Setup

1. Flash `full` firmware
2. ESP32 creates AP **ESP32-S3-Setup** (open network)
3. Connect phone/laptop to that AP
4. Captive portal opens at **192.168.4.1**
5. Select your WiFi network, enter password, click **Connect**
6. Device reboots and connects to your WiFi
7. Open dashboard at the IP shown in serial monitor

## Factory Reset

```
http://<device-ip>/api/factory-reset
```

Or click **Factory Reset** on the dashboard. Clears WiFi credentials + reboots into AP mode.

## Build Environments

| Environment | Contents | Use Case |
|---|---|---|
| `full` | All modules integrated | Production firmware |
| `test_cam` | Camera + WiFi + Stream | Verify camera hardware |
| `test_mic` | Audio + serial dump | Verify microphone |
| `test_wifi` | WiFi + Captive Portal | Verify WiFi setup |

Each test environment is independent — flash and test one module without affecting others.

## Configuration

Stored in **NVS** via `Preferences` in `"wifi"` / `"esp32sense"` namespaces.

| Key | Type | Default | Description |
|---|---|---|---|
| `wifi_ssid` | string | `""` | WiFi SSID |
| `wifi_pass` | string | `""` | WiFi password |
| `face_thresh` | float | `0.55` | Face recognition threshold |
| `wake_thresh` | float | `0.70` | Wake word confidence |
| `stream_enabled` | bool | `true` | Auto-start stream |
| `cam_res` | int | `6` (HVGA) | Camera resolution code |
