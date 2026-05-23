#pragma once
#include <Arduino.h>
#include "pins_config.h"

class LedIndicator {
public:
    enum class Pattern : uint8_t {
        OFF,
        SOLID,
        BLINK_FAST,
        BLINK_SLOW,
        PULSE,
    };

    void begin() {
        ledcSetup(LEDC_CHANNEL, 5000, 8);
        ledcAttachPin(Pins::LED_BUILTIN, LEDC_CHANNEL);
    }

    void setState(Pattern pattern = Pattern::SOLID) {
        m_pattern = pattern;
        m_lastToggle = 0;
        m_on = true;
    }

    void update() {
        unsigned long now = millis();
        uint32_t duty;

        switch (m_pattern) {
            case Pattern::OFF:
                duty = 0;
                break;

            case Pattern::SOLID:
                duty = 255;
                break;

            case Pattern::BLINK_FAST:
                if (now - m_lastToggle > 150) {
                    m_on = !m_on;
                    m_lastToggle = now;
                }
                duty = m_on ? 255 : 0;
                break;

            case Pattern::BLINK_SLOW:
                if (now - m_lastToggle > 500) {
                    m_on = !m_on;
                    m_lastToggle = now;
                }
                duty = m_on ? 255 : 0;
                break;

            case Pattern::PULSE: {
                float t = (now % 2000) / 2000.0f;
                duty = (sinf(t * 2.0f * 3.14159f) + 1.0f) * 127.5f;
                break;
            }
        }

        ledcWrite(LEDC_CHANNEL, duty);
    }

private:
    static constexpr int LEDC_CHANNEL = 0;
    Pattern m_pattern = Pattern::OFF;
    unsigned long m_lastToggle = 0;
    bool m_on = true;
};
