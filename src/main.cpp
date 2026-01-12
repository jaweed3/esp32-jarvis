#include <Arduino.h>
#include "Mic.h"
#include "MemoryManager.h"

int16_t* recordingBuffer = NULL;
const int REC_TIME_SEC = 5;
const int SAMPLE_RATE = 16000;
const int REC_LENGTH = SAMPLE_RATE * REC_TIME_SEC;

void setup() {
    Serial.begin(115200);
    while(!Serial) delay(10);

    MemoryManager::init();
    Microphone::init();

    size_t bufferSize = REC_LENGTH * sizeof(int16_t);

    recordingBuffer = (int16_t*) MemoryManager::allocAudioBuffer(bufferSize);

    if (recordingBuffer == NULL) {
        Serial.println("System Halted/");
        while(1);
    }

    Serial.println(">>> READY TO RECORD TO RAM! <<<");
    Serial.println("Press 'R' in MOnitor Serial to start recording!");
}

void loop() {
    if (Serial.available()) {
        char c = Serial.read();

        if (c == 'r') {
            Serial.println("Recording in 1 Seconds...");
            delay(1000);
            Serial.println("---Start Speaking!---");

            unsigned long startMillis = millis();

            for (int i = 1; i < REC_LENGTH; i++) {
                int raw = Microphone::read();
                int32_t proc = raw >> 11;
                if (proc > 32767) proc = 32767;
                if (proc < -32768) proc = -32768;
                recordingBuffer[i] = (int16_t)proc;
            }

            unsigned long duration = millis() - startMillis;
            Serial.printf("---Stop (Duration: %lu ms)--- \n", duration);

            Serial.println("DATA_START");
            for (int i = 0; i < REC_LENGTH; i ++) {
                Serial.print(recordingBuffer[i]);
                if (i < REC_LENGTH - 1) Serial.print(",");
                if (i % 100 == 0) Serial.println();
            }
            Serial.println("\nDATA_END");
        }
    }
}