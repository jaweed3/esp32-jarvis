#pragma once
#include <Arduino.h>
#include "core/EventBus.h"
#include "core/StateMachine.h"
#include "memory/MemoryManager.h"
#include "wifi/WifiManager.h"
#include "wifi/CaptivePortal.h"
#include "audio/AudioManager.h"
#include "vision/CameraManager.h"
#include "server/HttpServer.h"
#include "storage/ConfigManager.h"

class SystemManager {
public:
    static SystemManager& instance() {
        static SystemManager mgr;
        return mgr;
    }

    void begin() {
        Serial.begin(115200);
        delay(500);
        Serial.println("\n\n=== ESP32-S3 NEURAL VISION v1.0 ===");

        // 1. Memory
        MemoryManager::init();

        // 2. EventBus
        if (!m_eventBus.begin(32)) {
            Serial.println("FATAL: EventBus init failed");
            return;
        }

        // 3. Config (NVS)
        ConfigManager::begin();

        // 4. Audio
        if (!AudioManager::init(16000, 16, 3)) {
            Serial.println("WARN: Audio init failed");
        } else {
            AudioManager::startCapture();
        }

        // 5. Camera
        if (!CameraManager::init(FRAMESIZE_HVGA, 12)) {
            Serial.println("WARN: Camera init failed");
        }

        // 6. State Machine
        setupStateMachine();
        m_stateMachine.begin();

        // 7. HTTP Server
        if (!m_server.begin(80)) {
            Serial.println("WARN: HTTP server init failed");
        } else {
            setupRoutes();
        }

        MemoryManager::printBudget();

        // 8. WiFi (triggers state transition)
        WifiManager::begin();
        if (WifiManager::isConnected()) {
            m_stateMachine.transitionTo(DeviceState::IDLE);
        } else {
            m_stateMachine.transitionTo(DeviceState::AP_MODE);
        }

        Serial.println("=== SYSTEM READY ===");
    }

    void run() {
        // Process events
        EventMessage msg;
        while (m_eventBus.receive(msg, 0)) {
            handleEvent(msg);
        }

        // Captive portal DNS (only active in AP_MODE)
        if (m_stateMachine.current() == DeviceState::AP_MODE) {
            CaptivePortal::processDNS();
        }

        // Audio poll (continuous)
        if (AudioManager::isInitialized()) {
            AudioManager::poll();
        }

        // State timeout check
        m_stateMachine.update();
    }

    EventBus& events() { return m_eventBus; }
    HttpServer& server() { return m_server; }
    StateMachine& state() { return m_stateMachine; }

private:
    SystemManager() = default;

    void setupStateMachine() {
        // INIT → hardware init done in begin(), transitioned manually after WiFi check
        m_stateMachine.onEnter(DeviceState::INIT, []() {
            Serial.println("State: INIT — Initializing...");
        });

        // AP_MODE → start captive portal
        m_stateMachine.onEnter(DeviceState::AP_MODE, []() {
            Serial.println("State: AP_MODE — Starting captive portal...");
            WifiManager::startAP("ESP32-S3-Setup");
            HttpServer::setGlobalHandle(SystemManager::instance().server().handle());
            CaptivePortal::begin();
        });
        m_stateMachine.onExit(DeviceState::AP_MODE, []() {
            Serial.println("State: AP_MODE — Stopping captive portal");
        });

        // CONNECTING → trying to connect WiFi
        m_stateMachine.onEnter(DeviceState::CONNECTING, []() {
            Serial.println("State: CONNECTING — Attempting WiFi...");
            String ssid = WifiManager::savedSSID();
            String pass = WifiManager::savedPass();
            if (ssid.length() > 0) {
                if (WifiManager::connect(ssid.c_str(), pass.c_str())) {
                    SystemManager::instance().m_stateMachine.transitionTo(DeviceState::IDLE);
                } else {
                    SystemManager::instance().m_stateMachine.transitionTo(DeviceState::AP_MODE);
                }
            } else {
                SystemManager::instance().m_stateMachine.transitionTo(DeviceState::AP_MODE);
            }
        });

        // IDLE → online, streaming ready, wake word listening
        m_stateMachine.onEnter(DeviceState::IDLE, []() {
            Serial.printf("State: IDLE — Online at %s\n", WifiManager::getIP().c_str());
            SystemManager::instance().m_stateMachine.clearTimeout();
        });

        // ACTIVE → wake word triggered, face detection active
        m_stateMachine.onEnter(DeviceState::ACTIVE, []() {
            Serial.println("State: ACTIVE — Camera + Face detection active");
            SystemManager::instance().m_stateMachine.setTimeout(30000); // 30s auto-idle
        });
        m_stateMachine.onTimeout([]() {
            SystemManager::instance().m_stateMachine.transitionTo(DeviceState::IDLE);
        });

        // ERROR → recovery
        m_stateMachine.onEnter(DeviceState::ERROR, []() {
            Serial.println("State: ERROR — Auto-recovery in 5s...");
            SystemManager::instance().m_stateMachine.setTimeout(5000);
        });
    }

    void setupRoutes() {
        // MJPEG Stream
        m_server.onGet("/stream", [this](httpd_req_t* req) -> esp_err_t {
            return streamHandler(req);
        });

        // Single JPEG capture
        m_server.onGet("/capture", [](httpd_req_t* req) -> esp_err_t {
            camera_fb_t* fb = CameraManager::capture();
            if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
            httpd_resp_set_type(req, "image/jpeg");
            httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
            esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
            CameraManager::returnFrame(fb);
            return res;
        });

        // Status API (extended with state info)
        m_server.onGet("/api/status", [this](httpd_req_t* req) -> esp_err_t {
            char buf[512];
            snprintf(buf, sizeof(buf),
                R"({"uptime_ms":%lu,"state":"%s","psram_free":%d,"dram_free":%d,"wifi_connected":%s,"rssi":%d,"ip":"%s","audio_energy":%.1f})",
                millis(),
                m_stateMachine.stateName(m_stateMachine.current()),
                MemoryManager::getFreePSRAM(),
                MemoryManager::getFreeDRAM(),
                WifiManager::isConnected() ? "true" : "false",
                WifiManager::getRSSI(),
                WifiManager::getIP().c_str(),
                AudioManager::isInitialized() ? AudioManager::getEnergy() : 0.0f);
            return HttpServer::serveJSON(req, buf);
        });

        // Config API
        m_server.onGet("/api/config", [](httpd_req_t* req) -> esp_err_t {
            return HttpServer::serveJSON(req, ConfigManager::toJSON().c_str());
        });

        // Factory reset
        m_server.onGet("/api/factory-reset", [](httpd_req_t* req) -> esp_err_t {
            HttpServer::serveJSON(req, "{\"ok\":true,\"rebooting\":true}");
            delay(100);
            WifiManager::factoryReset();
            return ESP_OK;
        });

        // System reboot
        m_server.onPost("/api/system/reboot", [](httpd_req_t* req) -> esp_err_t {
            HttpServer::serveJSON(req, "{\"ok\":true}");
            delay(100);
            ESP.restart();
            return ESP_OK;
        });

        // Dashboard
        m_server.onGet("/", [this](httpd_req_t* req) -> esp_err_t {
            return HttpServer::serveHTML(req, DASHBOARD_HTML);
        });
    }

    static esp_err_t streamHandler(httpd_req_t* req) {
        char partBuf[64];
        esp_err_t res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
        if (res != ESP_OK) return ESP_FAIL;
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

        while (true) {
            camera_fb_t* fb = CameraManager::capture();
            if (!fb) {
                res = ESP_FAIL;
            } else {
                if (res == ESP_OK) {
                    size_t hlen = snprintf(partBuf, sizeof(partBuf),
                        "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
                    res = httpd_resp_send_chunk(req, partBuf, hlen);
                }
                if (res == ESP_OK)
                    res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
                if (res == ESP_OK)
                    res = httpd_resp_send_chunk(req, "\r\n--frame\r\n", 12);
                CameraManager::returnFrame(fb);
            }
            if (res != ESP_OK) break;
        }
        return res;
    }

    void handleEvent(const EventMessage& msg) {
        switch (msg.event) {
            case SystemEvent::WAKE_WORD_DETECTED:
                Serial.println("Event: Wake word detected!");
                if (m_stateMachine.current() == DeviceState::IDLE) {
                    m_stateMachine.transitionTo(DeviceState::ACTIVE);
                }
                break;
            case SystemEvent::FACE_DETECTED:
                Serial.printf("Event: Face [%d,%d,%d,%d]\n",
                    msg.data[0], msg.data[1], msg.data[2], msg.data[3]);
                break;
            case SystemEvent::ERROR_OCCURRED:
                Serial.printf("Event: Error code %d\n", msg.data[0]);
                m_stateMachine.transitionTo(DeviceState::ERROR);
                break;
            default:
                break;
        }
    }

    EventBus m_eventBus;
    StateMachine m_stateMachine;
    HttpServer m_server;

    static constexpr const char* DASHBOARD_HTML = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32-S3 Neural Vision</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0f0f1a;color:#e0e0e0;font-family:system-ui,sans-serif;display:flex;height:100vh}
  .sidebar{width:300px;background:#1a1a2e;padding:20px;display:flex;flex-direction:column;gap:14px;overflow-y:auto}
  .main{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}
  .logo{font-size:18px;font-weight:700;color:#7c8aff}
  .tagline{font-size:11px;color:#666;margin-top:-8px}
  .card{background:#16162b;border-radius:12px;padding:14px;border:1px solid #252545}
  .card h3{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:8px}
  .stat{display:flex;justify-content:space-between;padding:3px 0;font-size:12px}
  .stat span:first-child{color:#999}
  .stat span:last-child{color:#c0c0ff;font-family:monospace}
  #stream-container{border-radius:12px;overflow:hidden;border:2px solid #2a2a4a;max-width:640px}
  #stream{display:block;width:100%}
  .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
  .dot.on{background:#4f8;box-shadow:0 0 6px #4f8}
  .dot.off{background:#f44;box-shadow:0 0 6px #f44}
  .log-entry{font-size:10px;color:#aaa;padding:1px 0;font-family:monospace}
  .btn{padding:8px 14px;border:none;border-radius:6px;background:#7c8aff;color:#fff;font-size:11px;cursor:pointer}
  .btn.danger{background:#8a2040}
</style>
</head>
<body>
<div class="sidebar">
  <div class="logo">Neural Vision</div>
  <div class="tagline">ESP32-S3 Edge AI</div>
  <div class="card">
    <h3>System</h3>
    <div class="stat"><span>State</span><span id="s-state"><span class="dot on"></span>IDLE</span></div>
    <div class="stat"><span>Uptime</span><span id="s-uptime">--</span></div>
    <div class="stat"><span>PSRAM</span><span id="s-psram">--</span></div>
    <div class="stat"><span>WiFi</span><span id="s-rssi">--</span></div>
    <div class="stat"><span>Audio</span><span id="s-audio">--</span></div>
  </div>
  <div class="card">
    <h3>Detection Log</h3>
    <div id="log"><span class="log-entry">Ready.</span></div>
  </div>
  <button class="btn danger" onclick="if(confirm('Reset?'))fetch('/api/factory-reset')">Factory Reset</button>
</div>
<div class="main">
  <div id="stream-container">
    <img id="stream" src="/stream" onerror="setTimeout(()=>{this.src='/stream?t='+Date.now()},1000)">
  </div>
</div>
<script>
  const $ = id => document.getElementById(id);
  setInterval(async () => {
    try {
      const r = await fetch('/api/status');
      const d = await r.json();
      $('s-uptime').textContent = (d.uptime_ms/1000).toFixed(0) + 's';
      $('s-psram').textContent = (d.psram_free/1024).toFixed(0) + ' KB';
      $('s-rssi').textContent = d.rssi + ' dBm';
      $('s-audio').textContent = d.audio_energy.toFixed(0);
      const dot = d.state === 'IDLE' || d.state === 'ACTIVE' ? '<span class="dot on"></span>' : '<span class="dot off"></span>';
      $('s-state').innerHTML = dot + d.state;
    } catch(e) {}
  }, 3000);
</script>
</body>
</html>
)rawliteral";
};
