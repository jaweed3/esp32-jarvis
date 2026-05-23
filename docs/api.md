# API Reference

## HTTP Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard SPA with live status |
| `GET` | `/stream` | MJPEG camera stream (`multipart/x-mixed-replace`) |
| `GET` | `/capture` | Single JPEG photo |
| `GET` | `/api/status` | System status (JSON) |
| `GET` | `/api/config` | Configuration (JSON) |
| `GET` | `/api/factory-reset` | Clear WiFi credentials + reboot |
| `POST` | `/api/system/reboot` | Reboot device |

---

### `GET /api/status`

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

| Field | Type | Description |
|---|---|---|
| `uptime_ms` | int | Milliseconds since boot |
| `state` | string | Current device state |
| `psram_free` | int | Free PSRAM (bytes) |
| `dram_free` | int | Free DRAM (bytes) |
| `wifi_connected` | bool | WiFi STA status |
| `rssi` | int | WiFi signal strength (dBm) |
| `ip` | string | Device IP address |
| `audio_energy` | float | Current audio energy level |

### `GET /api/config`

```json
{
  "wifi_ssid": "MyNetwork",
  "face_threshold": 0.55,
  "wake_threshold": 0.70,
  "stream_enabled": true,
  "cam_resolution": 6
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `wifi_ssid` | string | `""` | Saved WiFi SSID |
| `face_thresh` | float | `0.55` | Face recognition confidence threshold |
| `wake_thresh` | float | `0.70` | Wake word detection confidence |
| `stream_enabled` | bool | `true` | Auto-start MJPEG stream |
| `cam_res` | int | `6` (HVGA) | Camera resolution code (`framesize_t`) |

### `GET /capture`

Returns a single JPEG image (`image/jpeg`). Use for snapshots or periodic capture.

### `GET /stream`

MJPEG multipart stream (`multipart/x-mixed-replace;boundary=frame`). Supports CORS for cross-origin clients.

### `GET /api/factory-reset`

Clears saved WiFi credentials from NVS and reboots into AP mode.

### `POST /api/system/reboot`

Reboots the device immediately. Body is ignored.

---

## Configuration Storage

Stored in **NVS** via `Preferences` library in the `"wifi"` and `"esp32sense"` namespaces.

| Key | Type | Default | Writable |
|---|---|---|---|
| `wifi_ssid` | string | `""` | Captive Portal |
| `wifi_pass` | string | `""` | Captive Portal |
| `face_thresh` | float | `0.55` | — |
| `wake_thresh` | float | `0.70` | — |
| `stream_enabled` | bool | `true` | — |
| `cam_res` | int | `6` (HVGA) | — |

Config values are loaded at boot from NVS. Future phases will add POST endpoints for runtime configuration.
