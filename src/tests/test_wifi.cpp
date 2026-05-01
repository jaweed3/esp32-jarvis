// Test: WiFi Manager — AP mode + Captive Portal + STA connect
// Build: pio run -e test_wifi -t upload
// Monitor: pio device monitor -e test_wifi
//
// Verifikasi:
//   1. Boot → check NVS for saved credentials
//   2. If saved → connect STA, show IP
//   3. If not saved → start AP "ESP32-S3-Setup", captive portal at 192.168.4.1
//   4. Di captive portal: scan WiFi, pilih network, input password → auto-reboot

#include <Arduino.h>
#include <WiFi.h>
#include "wifi/WifiManager.h"
#include "wifi/CaptivePortal.h"
#include "server/HttpServer.h"
#include "memory/MemoryManager.h"

HttpServer server;

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n=== TEST: WiFi Manager ===");

    MemoryManager::init();

    // Cek NVS
    WifiManager::begin();

    if (WifiManager::isConnected()) {
        // STA mode — simple status page
        if (!server.begin(80)) {
            Serial.println("Server init failed");
            return;
        }

        server.onGet("/", [](httpd_req_t* req) -> esp_err_t {
            String html = "<h2>WiFi Connected!</h2>";
            html += "<p>SSID: " + WifiManager::savedSSID() + "</p>";
            html += "<p>IP: " + WifiManager::getIP() + "</p>";
            html += "<p>RSSI: " + String(WifiManager::getRSSI()) + " dBm</p>";
            html += "<p><a href='/factory-reset'>Factory Reset</a></p>";
            return HttpServer::serveHTML(req, html.c_str());
        });

        server.onGet("/factory-reset", [](httpd_req_t* req) -> esp_err_t {
            HttpServer::serveHTML(req, "<h2>Resetting...</h2><meta http-equiv='refresh' content='3'>");
            delay(100);
            WifiManager::factoryReset();
            return ESP_OK;
        });

        Serial.printf("IP: %s\n", WifiManager::getIP().c_str());
    } else {
        // AP mode
        WifiManager::startAP("ESP32-S3-Setup");

        if (!server.begin(80)) {
            Serial.println("Server init failed");
            return;
        }

        // Set global HTTP handle biar CaptivePortal bisa register routes
        HttpServer::setGlobalHandle(server.handle());

        CaptivePortal::begin();

        Serial.println("AP Mode: ESP32-S3-Setup");
        Serial.println("Open: http://192.168.4.1");
    }

    Serial.println("=== TEST READY ===\n");
}

void loop() {
    // Process DNS requests (captive portal)
    CaptivePortal::processDNS();
    vTaskDelay(pdMS_TO_TICKS(100));
}
