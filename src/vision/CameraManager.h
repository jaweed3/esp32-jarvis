#pragma once
#include "esp_camera.h"
#include "Arduino.h"
#include "pins_config.h"

class CameraManager {
public:
    static bool init(framesize_t frameSize = FRAMESIZE_HVGA, int jpegQuality = 12) {
        camera_config_t config;
        config.ledc_channel = LEDC_CHANNEL_0;
        config.ledc_timer = LEDC_TIMER_0;
        config.pin_d0 = Pins::Y2;
        config.pin_d1 = Pins::Y3;
        config.pin_d2 = Pins::Y4;
        config.pin_d3 = Pins::Y5;
        config.pin_d4 = Pins::Y6;
        config.pin_d5 = Pins::Y7;
        config.pin_d6 = Pins::Y8;
        config.pin_d7 = Pins::Y9;
        config.pin_xclk = Pins::XCLK;
        config.pin_pclk = Pins::PCLK;
        config.pin_vsync = Pins::VSYNC;
        config.pin_href = Pins::HREF;
        config.pin_sccb_sda = Pins::SIOD;
        config.pin_sccb_scl = Pins::SIOC;
        config.pin_pwdn = Pins::PWDN;
        config.pin_reset = Pins::RESET;
        config.xclk_freq_hz = 20000000;
        config.pixel_format = PIXFORMAT_JPEG;

        if (psramFound()) {
            config.frame_size = frameSize;
            config.jpeg_quality = jpegQuality;
            config.fb_count = 2;
            config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
            config.fb_location = CAMERA_FB_IN_DRAM;
        } else {
            config.frame_size = FRAMESIZE_QVGA;
            config.jpeg_quality = jpegQuality;
            config.fb_count = 1;
            config.fb_location = CAMERA_FB_IN_DRAM;
        }

        esp_err_t err = esp_camera_init(&config);
        if (err != ESP_OK) {
            Serial.printf("Camera init failed: 0x%x\n", err);
            return false;
        }

        m_sensor = esp_camera_sensor_get();
        m_initialized = true;
        m_resolution = frameSize;
        Serial.println("Camera OK!");
        return true;
    }

    static camera_fb_t* capture() {
        return esp_camera_fb_get();
    }

    static void returnFrame(camera_fb_t* fb) {
        if (fb) esp_camera_fb_return(fb);
    }

    static sensor_t* getSensor() { return m_sensor; }

    static framesize_t getResolution() { return m_resolution; }

    static void setFlip(bool horizontal, bool vertical) {
        if (m_sensor) {
            m_sensor->set_hmirror(m_sensor, horizontal);
            m_sensor->set_vflip(m_sensor, vertical);
        }
    }

    static void setBrightness(int brightness) {
        if (m_sensor) m_sensor->set_brightness(m_sensor, brightness);
    }

    static bool isInitialized() { return m_initialized; }

private:
    static sensor_t* m_sensor;
    static framesize_t m_resolution;
    static bool m_initialized;
};

sensor_t* CameraManager::m_sensor = nullptr;
framesize_t CameraManager::m_resolution = FRAMESIZE_HVGA;
bool CameraManager::m_initialized = false;
