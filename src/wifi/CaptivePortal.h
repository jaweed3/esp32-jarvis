#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <DNSServer.h>
#include "server/HttpServer.h"
#include "wifi/WifiManager.h"

class CaptivePortal {
public:
    static void begin() {
        m_dnsServer.start(53, "*", WiFi.softAPIP());

        // Register captive portal handler on the main HTTP server
        httpd_handle_t handle = HttpServer::globalHandle();
        if (!handle) return;

        // Captive portal — semua request yang bukan API/stream diarahkan ke sini
        httpd_uri_t root = {
            .uri = "/",
            .method = HTTP_GET,
            .handler = rootHandler,
            .user_ctx = nullptr
        };
        httpd_register_uri_handler(handle, &root);

        // WiFi scan API
        httpd_uri_t scan = {
            .uri = "/wifi-scan",
            .method = HTTP_GET,
            .handler = scanHandler,
            .user_ctx = nullptr
        };
        httpd_register_uri_handler(handle, &scan);

        // WiFi connect API
        httpd_uri_t connect = {
            .uri = "/wifi-connect",
            .method = HTTP_POST,
            .handler = connectHandler,
            .user_ctx = nullptr
        };
        httpd_register_uri_handler(handle, &connect);

        // Wildcard: redirect semua ke root
        httpd_uri_t wildcard = {
            .uri = "/*",
            .method = HTTP_GET,
            .handler = redirectHandler,
            .user_ctx = nullptr
        };
        httpd_register_uri_handler(handle, &wildcard);

        Serial.println("Captive Portal: ready");
    }

    static void processDNS() {
        m_dnsServer.processNextRequest();
    }

private:
    static esp_err_t rootHandler(httpd_req_t* req) {
        return HttpServer::serveHTML(req, SETUP_HTML);
    }

    static esp_err_t redirectHandler(httpd_req_t* req) {
        httpd_resp_set_status(req, "302 Found");
        httpd_resp_set_hdr(req, "Location", "/");
        return httpd_resp_send(req, nullptr, 0);
    }

    static esp_err_t scanHandler(httpd_req_t* req) {
        int n = WiFi.scanNetworks();
        String json = "[";
        for (int i = 0; i < n; i++) {
            if (i > 0) json += ",";
            json += "{\"ssid\":\"" + WiFi.SSID(i) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + ",\"secure\":" + String(WiFi.encryptionType(i) != WIFI_AUTH_OPEN) + "}";
        }
        json += "]";
        WiFi.scanDelete();
        return HttpServer::serveJSON(req, json.c_str());
    }

    static esp_err_t connectHandler(httpd_req_t* req) {
        char buf[128] = {};
        int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
        if (ret <= 0) {
            httpd_resp_send_500(req);
            return ESP_FAIL;
        }

        // Simple JSON parse: {"ssid":"...","pass":"..."}
        String body(buf);
        int ssidStart = body.indexOf("\"ssid\":\"") + 8;
        int ssidEnd = body.indexOf("\"", ssidStart);
        int passStart = body.indexOf("\"pass\":\"") + 8;
        int passEnd = body.indexOf("\"", passStart);

        if (ssidStart < 8 || passStart < 8) {
            return HttpServer::serveJSON(req, "{\"ok\":false,\"error\":\"invalid json\"}");
        }

        String ssid = body.substring(ssidStart, ssidEnd);
        String pass = body.substring(passStart, passEnd);

        Serial.printf("CaptivePortal: connecting to %s...\n", ssid.c_str());
        httpd_resp_set_type(req, "application/json");
        httpd_resp_sendstr(req, "{\"ok\":true,\"rebooting\":true}");

        // Simpan credentials lalu reboot
        delay(100);
        WifiManager::saveCredentials(ssid.c_str(), pass.c_str());
        delay(500);
        ESP.restart();
        return ESP_OK;
    }

    static constexpr const char* SETUP_HTML = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32-S3 Setup</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0f0f1a;color:#e0e0e0;font-family:system-ui,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px}
  .card{background:#1a1a2e;border-radius:16px;padding:32px 24px;max-width:400px;width:100%;border:1px solid #252545}
  h1{font-size:20px;text-align:center;color:#7c8aff;margin-bottom:4px}
  p{text-align:center;color:#666;font-size:12px;margin-bottom:24px}
  label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#888;display:block;margin:12px 0 4px}
  select,input{width:100%;padding:10px 12px;border-radius:8px;background:#0f0f1a;border:1px solid #333;color:#ccc;font-size:14px}
  select:focus,input:focus{outline:none;border-color:#7c8aff}
  button{width:100%;padding:12px;border:none;border-radius:8px;background:#7c8aff;color:#fff;font-size:14px;font-weight:600;cursor:pointer;margin-top:20px}
  button:hover{background:#9a9fff}
  button:disabled{opacity:.5;cursor:default}
  .status{text-align:center;font-size:12px;color:#888;margin-top:12px}
  .error{color:#f44}
</style>
</head>
<body>
<div class="card">
  <h1>ESP32-S3 Setup</h1>
  <p>Connect to your WiFi network</p>
  <label>WiFi Network</label>
  <select id="ssid" onchange="onSSIDChange()">
    <option value="">Scanning...</option>
  </select>
  <label>Password</label>
  <input id="pass" type="password" placeholder="Enter WiFi password">
  <button id="connect-btn" onclick="connect()">Connect</button>
  <div class="status" id="status"></div>
</div>
<script>
  async function scan(){
    try{
      const r=await fetch('/wifi-scan');
      const nets=await r.json();
      const sel=document.getElementById('ssid');
      sel.innerHTML='<option value="">Select network...</option>';
      nets.forEach(n=>{sel.innerHTML+=`<option value="${n.ssid}">${n.ssid} (${n.rssi}dBm) ${n.secure?'🔒':''}</option>`});
    }catch(e){setTimeout(scan,2000)}
  }
  function onSSIDChange(){
    const ssid=document.getElementById('ssid');
    const pass=document.getElementById('pass');
    const opt=ssid.options[ssid.selectedIndex];
    if(opt && opt.text.includes('🔒')) pass.parentElement.style.display='block';
    else pass.parentElement.style.display='none';
  }
  async function connect(){
    const ssid=document.getElementById('ssid').value;
    const pass=document.getElementById('pass').value;
    const btn=document.getElementById('connect-btn');
    const status=document.getElementById('status');
    if(!ssid){status.textContent='Select a network first';status.className='status error';return}
    btn.disabled=true;btn.textContent='Connecting...';status.textContent='Saving & rebooting...';status.className='status';
    await fetch('/wifi-connect',{method:'POST',body:JSON.stringify({ssid,pass})});
    setTimeout(()=>{status.textContent='Device is rebooting. Reconnect in a moment.'},1000);
  }
  scan();
</script>
</body>
</html>
)rawliteral";

    static DNSServer m_dnsServer;
};

DNSServer CaptivePortal::m_dnsServer;
