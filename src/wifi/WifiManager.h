#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <Preferences.h>

class WifiManager {
public:
    static void begin() {
        m_prefs.begin("wifi", false);

        if (hasSavedCredentials()) {
            String ssid = savedSSID();
            String pass = savedPass();
            connect(ssid.c_str(), pass.c_str());
        } else {
            startAP();
        }
    }

    // --- AP Mode ---
    static void startAP(const char* ssid = "ESP32-S3-Setup") {
        WiFi.mode(WIFI_AP);
        WiFi.softAP(ssid);
        Serial.printf("AP Mode: %s (IP: %s)\n", ssid, WiFi.softAPIP().toString().c_str());
    }

    // --- STA Mode ---
    static bool connect(const char* ssid, const char* pass) {
        WiFi.mode(WIFI_STA);
        WiFi.setSleep(false);
        WiFi.begin(ssid, pass);

        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 30) {
            delay(500);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED) {
            Serial.printf("\nWiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
            saveCredentials(ssid, pass);
            return true;
        }

        Serial.println("\nWiFi connection failed.");
        return false;
    }

    static void disconnect() {
        WiFi.disconnect(true);
    }

    static bool isConnected() {
        return WiFi.status() == WL_CONNECTED;
    }

    static String getIP() {
        return WiFi.localIP().toString();
    }

    static int getRSSI() {
        return WiFi.RSSI();
    }

    // --- Credential Persistence (NVS) ---
    static void saveCredentials(const char* ssid, const char* pass) {
        m_prefs.putString("ssid", ssid);
        m_prefs.putString("pass", pass);
    }

    static bool hasSavedCredentials() {
        String ssid = m_prefs.getString("ssid", "");
        return ssid.length() > 0;
    }

    static String savedSSID() {
        return m_prefs.getString("ssid", "");
    }

    static String savedPass() {
        return m_prefs.getString("pass", "");
    }

    static void clearCredentials() {
        m_prefs.remove("ssid");
        m_prefs.remove("pass");
    }

    static bool factoryReset() {
        clearCredentials();
        m_prefs.end();
        delay(100);
        ESP.restart();
        return true;
    }

private:
    static Preferences m_prefs;
};

Preferences WifiManager::m_prefs;
