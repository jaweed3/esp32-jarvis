# Troubleshooting

## Flash fails / "Failed to connect to ESP32-S3"

**Cause**: Wrong serial port auto-detected, or board not in download mode.

**Solutions**:

```bash
# 1. Set port explicitly in platformio.ini
upload_port = /dev/cu.usbmodem31301

# 2. Enable verbose upload to see the real error
pio run -e full -t upload --verbose

# 3. Put board in download mode:
#    Hold BOOT → tap RESET → release BOOT

# 4. Try lower baud rate
upload_speed = 115200
```

## "tcpip_send_msg_wait_sem (Invalid mbox)" crash

**Cause**: WiFi/HTTP stack used before lwIP was initialized.

**Fix**: Already applied — `WiFi.mode(WIFI_AP_STA)` is now called before the HTTP server starts. If you see this in custom code, ensure lwIP is initialized before any network calls.

## Board boots but no serial output

1. Enable **USB CDC on Boot**: add `-DARDUINO_USB_CDC_ON_BOOT=1` in build flags
2. Press **RESET** once after flash
3. Power-cycle: unplug USB, wait 3s, re-plug

## ESP32 stuck in download mode

If you see `waiting for download` in the serial output:

1. Press the **RESET** button once
2. If still stuck, press and hold **BOOT** → press **RESET** → release **BOOT** → release **RESET**
3. Power-cycle (unplug/replug USB)

## Onboard LED stays off

- GPIO21 is the USER LED, active **HIGH**
- GPIO21 is also shared with the SD card CS — if you use the SD card, the LED flickers during I/O
- Test manually: `digitalWrite(21, HIGH)` should turn it on
- Check that `LedIndicator::begin()` is called

## Serial monitor shows garbled text

**Fix**: Set baud rate to `115200` in your monitor to match `monitor_speed` in `platformio.ini`.

## WiFi AP doesn't appear

1. Press **RESET** once — board may be in download mode
2. If still missing, hold **BOOT** for 2s then release
3. Check serial output for `StateMachine: INIT -> AP_MODE`

## "psramInit(): PSRAM enabled" not showing

PSRAM is required — firmware won't work without it.

Verify in `platformio.ini`:
```ini
board_build.arduino.memory_type = qio_opi
build_flags = -DBOARD_HAS_PSRAM
```

## Multiple definition of `setup()` / `loop()` at link time

**Cause**: Test files (`tests/*.cpp`) leaking into the `full` build.

**Fix**: Ensure `build_src_filter` in `[env:full]` has:
```ini
build_src_filter =
    +<*>
    -<tests/*.cpp>
```

## Resources

- [ESP32-S3 esptool troubleshooting](https://docs.espressif.com/projects/esptool/en/latest/troubleshooting.html)
- [Seeed XIAO ESP32-S3 forum](https://forum.seeedstudio.com/c/xiao-series/)
- [ESP32-S3 datasheet](https://www.espressif.com/en/products/socs/esp32-s3)
