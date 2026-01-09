// testing mic
#include <Arduino.h>
#include "Mic.h"

void setup() {
    Serial.begin(115200);
    while(!Serial) delay(10);
    Microphone::init();
}

void loop() {
    Microphone::readAndPlot();
}