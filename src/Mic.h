#pragma once
#include <Arduino.h>
#include <I2S.h>

class Microphone {
public:
    static void init() {
        Serial.println("---INIT MICROPHONE---");

        I2S.setAllPins(-1, 42, 41, -1, -1);
        
        if(!I2S.begin(PDM_MONO_MODE, 16000, 16)) {
            Serial.println("Failed to initiate I2S");
            while(1);
        }

        Serial.println("Microphone OK! Listening!...");
    }

    static int16_t read() {
        return (int16_t)I2S.read();
    }
};