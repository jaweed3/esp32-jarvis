#pragma once
#include <Arduino.h>
#include "esp_heap_caps.h"

class MemoryManager {
public:
    static void init() {
        Serial.println(">>> Initialize the Memory <<<");
        
        if (psramFound()) {
            Serial.printf("PSRAM Detected! Total>: %d btyes\n", ESP.getPsramSize());
            Serial.printf("PSRAM Free: %d bytes\n", ESP.getFreePsram());
        } else {
            Serial.println(("FATAL : PSRAM is not found! check 'PSRAM: OPI'"));
            while (1)
            {
                delay(100);
            }
            
        }
    }

    static void* allocAudioBuffer(size_t size) {
        void* ptr = heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

        if (ptr == NULL ){
            Serial.printf("FAILED TO ALLOCATE %d bytes in PSRAM! remaining PSRAM: %d\n ", size, ESP.getFreePsram());
            return NULL;
        }

        Serial.printf("Successfully Allocate %d bytes in PSRAM. Address: %p\n", size, ptr);
        return ptr;
    }

    static void freeBuffer(void* ptr) {
        heap_caps_free(ptr);
    }
};