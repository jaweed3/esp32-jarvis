// Test: Microphone — PSRAM recording & serial dump
// Build: pio run -e test_mic -t upload
// Monitor: pio device monitor -e test_mic
//
// Verifikasi: ketik 'r' di serial monitor untuk record 5 detik.
// Audio akan di-dump sebagai CSV via serial (bisa di-plot).

#include <Arduino.h>
#include "audio/AudioManager.h"
#include "memory/MemoryManager.h"

#define RECORD_SECONDS 5
#define SAMPLE_RATE    16000

void dumpAudio();

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    delay(500);
    Serial.println("\n=== TEST: Microphone ===");

    MemoryManager::init();

    if (!AudioManager::init(SAMPLE_RATE, 16, 5)) {
        Serial.println("FATAL: Audio init failed");
        while (1) delay(100);
    }

    AudioManager::startCapture();
    Serial.println("Audio ring buffer active.");
    Serial.println("Commands: 'r' = record 5s & dump, 'e' = check energy");
    Serial.println("=== TEST READY ===\n");
}

void loop() {
    // Continously fill ring buffer
    AudioManager::poll();

    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'r') {
            delay(500); // biarin buffer terisi dulu
            dumpAudio();
        } else if (c == 'e') {
            Serial.printf("Audio energy: %.1f (voice: %s)\n",
                          AudioManager::getEnergy(),
                          AudioManager::isVoiceActive(500.0f) ? "YES" : "no");
        }
    }

    delay(10);
}

void dumpAudio() {
    size_t samplesToRead = SAMPLE_RATE * RECORD_SECONDS;
    size_t avail = AudioManager::available();
    if (avail < samplesToRead) {
        Serial.printf("Not enough samples: %d available, need %d\n", avail, samplesToRead);
        return;
    }

    int16_t* buf = (int16_t*)MemoryManager::allocPSRAM(samplesToRead * sizeof(int16_t));
    if (!buf) { Serial.println("Alloc failed!"); return; }

    size_t read = AudioManager::readSamples(buf, samplesToRead);

    Serial.println("DATA_START");
    for (size_t i = 0; i < read; i++) {
        Serial.print(buf[i]);
        if (i < read - 1) Serial.print(",");
        if (i % 100 == 0) Serial.println();
    }
    Serial.println("\nDATA_END");
    Serial.printf("Dumped %d samples\n", read);

    MemoryManager::freePSRAM(buf);
}
