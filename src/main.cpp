#include <Arduino.h>
#include "core/SystemManager.h"

void setup() {
    SystemManager::instance().begin();
}

void loop() {
    SystemManager::instance().run();
    vTaskDelay(pdMS_TO_TICKS(10));
}
