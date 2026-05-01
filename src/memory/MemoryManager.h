#pragma once
#include <Arduino.h>
#include "esp_heap_caps.h"

class MemoryManager {
public:
    static void init() {
        Serial.println(">>> Memory Init <<<");

        if (psramFound()) {
            Serial.printf("PSRAM: %d bytes total, %d bytes free\n",
                          ESP.getPsramSize(), ESP.getFreePsram());
        } else {
            Serial.println("FATAL: PSRAM not found! Check 'PSRAM: OPI' in menuconfig.");
            while (1) { delay(100); }
        }

        Serial.printf("DRAM:  %d bytes free\n", ESP.getFreeHeap());
    }

    static void* allocPSRAM(size_t size) {
        void* ptr = heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
        if (!ptr) {
            Serial.printf("PSRAM alloc FAILED: %d bytes (free: %d)\n",
                          size, ESP.getFreePsram());
        }
        return ptr;
    }

    static void freePSRAM(void* ptr) {
        if (ptr) heap_caps_free(ptr);
    }

    static size_t getFreePSRAM() {
        return ESP.getFreePsram();
    }

    static size_t getFreeDRAM() {
        return ESP.getFreeHeap();
    }

    static void printBudget() {
        Serial.println("--- Memory Budget ---");
        Serial.printf("  PSRAM free: %d / %d bytes\n",
                      ESP.getFreePsram(), ESP.getPsramSize());
        Serial.printf("  DRAM free:  %d bytes\n", ESP.getFreeHeap());
        Serial.println("---------------------");
    }
};
