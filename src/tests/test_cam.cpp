// Test: Camera + WiFi + HTTP Stream
// Build: pio run -e test_cam -t upload
// Monitor: pio device monitor -e test_cam
//
// Verifikasi: setelah boot, buka browser ke IP ESP32 di Serial Monitor.
// Stream camera di /stream, capture di /capture.

#include <Arduino.h>
#include <WiFi.h>
#include "vision/CameraManager.h"
#include "wifi/WifiManager.h"
#include "server/HttpServer.h"
#include "memory/MemoryManager.h"

HttpServer server;

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n=== TEST: Camera + WiFi + Stream ===");

    // Memory
    MemoryManager::init();

    // Camera
    if (!CameraManager::init(FRAMESIZE_HVGA, 12)) {
        Serial.println("FATAL: Camera init failed");
        while (1) delay(100);
    }

    // WiFi — hardcoded for testing, or use NVS
    WifiManager::begin();
    if (!WifiManager::isConnected()) {
        // Fallback: coba connect manual (ganti SSID/PASS sesuai network lo)
        Serial.println("No saved WiFi. Trying manual connect...");
        // GANTI di sini buat testing:
        if (!WifiManager::connect("YOUR_SSID", "YOUR_PASSWORD")) {
            Serial.println("WiFi failed, starting AP mode...");
            WifiManager::startAP("ESP32-CAM-Test");
        }
    }

    // HTTP Server
    if (!server.begin(80)) {
        Serial.println("FATAL: Server init failed");
        while (1) delay(100);
    }

    // Routes
    server.onGet("/stream", [](httpd_req_t* req) -> esp_err_t {
        char partBuf[64];
        esp_err_t res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
        if (res != ESP_OK) return ESP_FAIL;
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        while (true) {
            camera_fb_t* fb = CameraManager::capture();
            if (!fb) { res = ESP_FAIL; break; }
            size_t hlen = snprintf(partBuf, sizeof(partBuf),
                                   "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
            httpd_resp_send_chunk(req, partBuf, hlen);
            httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
            httpd_resp_send_chunk(req, "\r\n--frame\r\n", 12);
            CameraManager::returnFrame(fb);
        }
        return res;
    });

    server.onGet("/capture", [](httpd_req_t* req) -> esp_err_t {
        camera_fb_t* fb = CameraManager::capture();
        if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
        httpd_resp_set_type(req, "image/jpeg");
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
        CameraManager::returnFrame(fb);
        return res;
    });

    server.onGet("/", [](httpd_req_t* req) -> esp_err_t {
        String html = "<h2>Camera Test</h2><img src='/stream'><br><a href='/capture'>Capture</a>";
        return HttpServer::serveHTML(req, html.c_str());
    });

    Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());
    Serial.println("Open browser -> http://" + WiFi.localIP().toString());
    Serial.println("=== TEST READY ===\n");
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
