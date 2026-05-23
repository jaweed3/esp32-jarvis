#pragma once

namespace Pins
{
    // Camera — OV2640/OV3660 parallel interface on Xiao ESP32-S3
    constexpr int PWDN  = -1;
    constexpr int RESET = -1;
    constexpr int XCLK  = 10;
    constexpr int SIOD  = 40;
    constexpr int SIOC  = 39;
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

    // Onboard WS2812 RGB LED
    constexpr int LED_BUILTIN = 21;
} // namespace Pins
