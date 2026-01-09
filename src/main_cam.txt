#include <Arduino.h>
#include <WiFi.h>
#include "Camera.cpp"
#include "Server.cpp"

const char* ssid = "MOVISTAR_6A18";
const char* password = "TYRYTVCJTYVKX4TbJYPY";

StreamServer visionServer;

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);

    if(!Camera::init()) {
        Serial.println("System Halted due to Camera failure.");
        while(true) delay(100);
     }

     WiFi.begin(ssid, password);
     WiFi.setSleep(false);

     Serial.print("Connected to wifi!");
     while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print("\nTrying to connect...\n");
     }
     Serial.println("\nConnected.");
     Serial.print("IP Address: ");
     Serial.println(WiFi.localIP());

     visionServer.start();
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}