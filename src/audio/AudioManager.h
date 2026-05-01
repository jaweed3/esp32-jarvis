#pragma once
#include <Arduino.h>
#include <I2S.h>
#include "memory/MemoryManager.h"

class AudioManager {
public:
    static bool init(uint32_t sampleRate = 16000, uint16_t sampleBits = 16,
                     size_t ringBufferSeconds = 3) {
        m_sampleRate = sampleRate;
        m_sampleBits = sampleBits;

        I2S.setAllPins(-1, 42, 41, -1, -1);
        if (!I2S.begin(PDM_MONO_MODE, sampleRate, sampleBits)) {
            Serial.println("Audio: I2S init failed!");
            return false;
        }

        m_ringSize = sampleRate * ringBufferSeconds;
        m_ringBuffer = (int16_t*)MemoryManager::allocPSRAM(m_ringSize * sizeof(int16_t));
        if (!m_ringBuffer) {
            Serial.println("Audio: ring buffer alloc failed!");
            return false;
        }

        m_initialized = true;
        Serial.printf("Audio OK! %dHz, ring=%d samples\n", sampleRate, m_ringSize);
        return true;
    }

    static void startCapture() {
        if (!m_initialized) return;
        m_capturing = true;
    }

    static void stopCapture() {
        m_capturing = false;
    }

    // Dipanggil dari audio task secara kontinyu
    static void poll() {
        if (!m_capturing) return;

        while (I2S.available()) {
            int16_t sample = (int16_t)I2S.read();
            m_ringBuffer[m_writeIdx] = sample;
            m_writeIdx = (m_writeIdx + 1) % m_ringSize;
            if (m_writeIdx == m_readIdx) {
                m_readIdx = (m_readIdx + 1) % m_ringSize; // overwrite oldest
            }

            // Simple energy VAD
            float absVal = abs(sample);
            m_energyAvg = m_energyAvg * 0.95f + absVal * 0.05f;
        }
    }

    // Baca N samples dari ring buffer ke buffer tujuan
    static size_t readSamples(int16_t* dst, size_t count) {
        size_t avail = available();
        if (count > avail) count = avail;

        for (size_t i = 0; i < count; i++) {
            dst[i] = m_ringBuffer[m_readIdx];
            m_readIdx = (m_readIdx + 1) % m_ringSize;
        }
        return count;
    }

    static size_t available() {
        if (m_writeIdx >= m_readIdx) return m_writeIdx - m_readIdx;
        return m_ringSize - m_readIdx + m_writeIdx;
    }

    static bool isVoiceActive(float threshold = 500.0f) {
        return m_energyAvg > threshold;
    }

    static float getEnergy() { return m_energyAvg; }
    static uint32_t getSampleRate() { return m_sampleRate; }
    static bool isInitialized() { return m_initialized; }

private:
    static int16_t* m_ringBuffer;
    static volatile size_t m_writeIdx;
    static volatile size_t m_readIdx;
    static size_t m_ringSize;
    static uint32_t m_sampleRate;
    static uint16_t m_sampleBits;
    static float m_energyAvg;
    static bool m_capturing;
    static bool m_initialized;
};

int16_t* AudioManager::m_ringBuffer = nullptr;
volatile size_t AudioManager::m_writeIdx = 0;
volatile size_t AudioManager::m_readIdx = 0;
size_t AudioManager::m_ringSize = 0;
uint32_t AudioManager::m_sampleRate = 16000;
uint16_t AudioManager::m_sampleBits = 16;
float AudioManager::m_energyAvg = 0.0f;
bool AudioManager::m_capturing = false;
bool AudioManager::m_initialized = false;
