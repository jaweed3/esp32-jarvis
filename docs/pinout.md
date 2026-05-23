# Pinout — Seeed Studio XIAO ESP32S3 Sense

Based on the [official Seeed Studio wiki](https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/).

## Main Board Pins

| Pin | GPIO | Function | Notes |
|-----|------|----------|-------|
| D0 | GPIO1 | ADC1 / TOUCH1 | |
| D1 | GPIO2 | ADC1 / TOUCH2 | |
| D2 | GPIO3 | ADC1 / TOUCH3 | Shared with SD CS |
| D3 | GPIO4 | ADC1 / TOUCH4 | |
| D4 | GPIO5 | ADC1 / TOUCH5, I2C SDA | |
| D5 | GPIO6 | ADC1 / TOUCH6, I2C SCL | |
| D6/TX | GPIO43 | UART0 TX | Strapping pin |
| D7/RX | GPIO44 | UART0 RX | Strapping pin |
| D8 | GPIO7 | ADC2 / TOUCH7, SPI SCK | Shared with SD SCK |
| D9 | GPIO8 | ADC2 / TOUCH8, SPI MISO | Shared with SD MISO |
| D10 | GPIO9 | ADC2 / TOUCH9, SPI MOSI | Shared with SD MOSI |
| — | GPIO21 | **USER LED** (orange) | Active HIGH, also SD CS |
| 5V | VBUS | Power input/output | USB voltage |
| 3V3 | 3V3_OUT | Regulated 700mA max | Power output |
| GND | GND | Ground | |

> ⚠ D6 (GPIO43) and D7 (GPIO44) are strapping pins — avoid driving them during boot.

## Sense Expansion Board

### OV2640 Camera (DVP parallel + I2C)

| Signal | GPIO | Signal | GPIO |
|--------|------|--------|------|
| XCLK | 10 | DVP_Y8 | 11 |
| DVP_PCLK | 13 | DVP_Y7 | 12 |
| DVP_VSYNC | 38 | DVP_Y6 | 14 |
| DVP_HREF | 47 | DVP_Y5 | 16 |
| CAM_SDA | 40 | DVP_Y4 | 18 |
| CAM_SCL | 39 | DVP_Y3 | 17 |
| — | — | DVP_Y2 | 15 |
| — | — | DVP_Y9 | 48 |

### PDM Microphone

| Signal | GPIO |
|--------|------|
| PDM CLK | 42 |
| PDM DATA | 41 |

> To free D11/D12 (GPIO41/42) for other use, cut the J1/J2 jumper on the back of the Sense board. This disables the microphone.

### MicroSD Card (SPI mode)

| Signal | GPIO | Main Board Pin |
|--------|------|----------------|
| CS | 3 | D2 |
| SCK | 7 | D8 |
| MISO | 8 | D9 |
| MOSI | 9 | D10 |

> To use the SPI pins instead of the SD card, cut the J3 jumper on the Sense board.

## Camera Pin Mapping (pins_config.h)

```cpp
namespace Pins {
    constexpr int PWDN  = -1;    // Not used
    constexpr int RESET = -1;    // Not used
    constexpr int XCLK  = 10;
    constexpr int SIOD  = 40;    // I2C SDA
    constexpr int SIOC  = 39;    // I2C SCL
    constexpr int Y9    = 48;
    constexpr int Y8    = 11;
    constexpr int Y7    = 12;
    constexpr int Y6    = 14;
    constexpr int Y5    = 16;
    constexpr int Y4    = 18;
    constexpr int Y3    = 17;
    constexpr int Y2    = 15;
    constexpr int VSYNC = 38;
    constexpr int HREF  = 47;
    constexpr int PCLK  = 13;
    constexpr int LED_BUILTIN = 21;
}
```

## Wiring Diagram

![Wiring Diagram](../wiring_diagram.png)
