#pragma once
#include <Arduino.h>
#include <driver/i2s.h>

#define I2S_SD      42
#define I2S_WS      41
#define I2S_SCK     43
#define I2S_PORT    I2S_NUM_0
#define SAMPLE_RATE 16000
#define BUFFER_LEN  1024

class Microphone {
public:
    static void init() {
        Serial.println("---INIT MICROPHONE---");

        i2s_config_t i2s_config = {
            .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
            .sample_rate = SAMPLE_RATE,
            .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
            .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
            .communication_format = I2S_COMM_FORMAT_STAND_I2S,
            .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
            .dma_buf_count = 4,
            .dma_buf_len = BUFFER_LEN,
            .use_apll = false
        };

        i2s_pin_config_t pin_config = {
            .bck_io_num = I2S_SCK,
            .ws_io_num = I2S_WS,
            .data_out_num = -1,
            .data_in_num = I2S_SD
        };

        if (i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL) != ESP_OK) {
            Serial.println("I2S Driver install failed.");
            while (true);
        }

        if (i2s_set_pin(I2S_PORT, &pin_config) != ESP_OK) {
            Serial.println("I2S Pin Config Failed!");
            while (true);
        }

        Serial.println("Microphone OK! Listening....");
    }

    static void readAndPlot() {
        int32_t sample_buffer[BUFFER_LEN];
        size_t bytes_read = 0;

        i2s_read(I2S_PORT, (void*)sample_buffer, BUFFER_LEN * sizeof(int32_t), &bytes_read, portMAX_DELAY);

        int samples_read = bytes_read / sizeof(int32_t);
        for (int i = 0; i < samples_read; i += 16) {
            int32_t sample = sample_buffer[i] >> 14;

            Serial.print("-2000 ");
            Serial.print("2000");
            Serial.println(sample);
        }
    }
};