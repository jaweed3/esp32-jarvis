#pragma once
#include "Arduino.h"
#include "esp_camera.h"
#include "esp_http_server.h"
#include <functional>

class HttpServer {
public:
    using HandlerFn = std::function<esp_err_t(httpd_req_t*)>;

    bool begin(uint16_t port = 80) {
        m_config = HTTPD_DEFAULT_CONFIG();
        m_config.server_port = port;

        if (httpd_start(&m_handle, &m_config) != ESP_OK) {
            Serial.println("HTTP Server: start failed!");
            return false;
        }

        Serial.printf("HTTP Server: port %d\n", port);
        return true;
    }

    void stop() {
        if (m_handle) {
            httpd_stop(m_handle);
            m_handle = nullptr;
        }
    }

    void on(const char* uri, httpd_method_t method, HandlerFn handler) {
        auto* ctx = new HandlerCtx{handler, m_handle};
        httpd_uri_t desc = {
            .uri = uri,
            .method = method,
            .handler = [](httpd_req_t* req) -> esp_err_t {
                auto* ctx = (HandlerCtx*)req->user_ctx;
                return ctx->fn(req);
            },
            .user_ctx = ctx
        };
        httpd_register_uri_handler(m_handle, &desc);
    }

    void onGet(const char* uri, HandlerFn handler) {
        on(uri, HTTP_GET, handler);
    }

    void onPost(const char* uri, HandlerFn handler) {
        on(uri, HTTP_POST, handler);
    }

    static esp_err_t serveText(httpd_req_t* req, const char* text, const char* contentType = "text/plain") {
        httpd_resp_set_type(req, contentType);
        httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
        return httpd_resp_send(req, text, HTTPD_RESP_USE_STRLEN);
    }

    static esp_err_t serveJSON(httpd_req_t* req, const char* json) {
        return serveText(req, json, "application/json");
    }

    static esp_err_t serveHTML(httpd_req_t* req, const char* html) {
        return serveText(req, html, "text/html");
    }

    httpd_handle_t handle() const { return m_handle; }

    // Global handle — untuk CaptivePortal yg butuh akses raw httpd
    static void setGlobalHandle(httpd_handle_t h) { s_globalHandle = h; }
    static httpd_handle_t globalHandle() { return s_globalHandle; }

private:
    struct HandlerCtx {
        HandlerFn fn;
        httpd_handle_t server;
    };

    httpd_handle_t m_handle = nullptr;
    httpd_config_t m_config;
    static httpd_handle_t s_globalHandle;
};

httpd_handle_t HttpServer::s_globalHandle = nullptr;
