#pragma once
#include <Arduino.h>
#include <Preferences.h>

class ConfigManager {
public:
    static void begin(const char* ns = "esp32sense") {
        m_prefs.begin(ns, false);
        m_namespace = ns;
    }

    // --- Typed Access ---
    static String getString(const char* key, const char* def = "") {
        return m_prefs.getString(key, def);
    }

    static bool setString(const char* key, const String& value) {
        return m_prefs.putString(key, value) > 0;
    }

    static int getInt(const char* key, int def = 0) {
        return m_prefs.getInt(key, def);
    }

    static bool setInt(const char* key, int value) {
        return m_prefs.putInt(key, value) > 0;
    }

    static float getFloat(const char* key, float def = 0.0f) {
        return m_prefs.getFloat(key, def);
    }

    static bool setFloat(const char* key, float value) {
        return m_prefs.putFloat(key, value) > 0;
    }

    static bool getBool(const char* key, bool def = false) {
        return m_prefs.getBool(key, def);
    }

    static bool setBool(const char* key, bool value) {
        return m_prefs.putBool(key, value) > 0;
    }

    // --- JSON Export for API ---
    static String toJSON() {
        String json = "{";
        json += "\"wifi_ssid\":\"" + getString(KEY_WIFI_SSID) + "\",";
        json += "\"face_threshold\":" + String(getFloat(KEY_FACE_THRESH, 0.55f)) + ",";
        json += "\"wake_threshold\":" + String(getFloat(KEY_WAKE_THRESH, 0.7f)) + ",";
        json += "\"stream_enabled\":" + String(getBool(KEY_STREAM_ENABLED, true) ? "true" : "false") + ",";
        json += "\"cam_resolution\":" + String(getInt(KEY_CAM_RES, (int)FRAMESIZE_HVGA));
        json += "}";
        return json;
    }

    // --- Factory Reset ---
    static void factoryReset() {
        m_prefs.clear();
        Serial.println("ConfigManager: factory reset done");
    }

    // --- Keys ---
    static constexpr const char* KEY_WIFI_SSID = "wifi_ssid";
    static constexpr const char* KEY_WIFI_PASS = "wifi_pass";
    static constexpr const char* KEY_FACE_THRESH = "face_thresh";
    static constexpr const char* KEY_WAKE_THRESH = "wake_thresh";
    static constexpr const char* KEY_CAM_RES = "cam_res";
    static constexpr const char* KEY_STREAM_ENABLED = "stream_en";

private:
    static Preferences m_prefs;
    static const char* m_namespace;
};

Preferences ConfigManager::m_prefs;
const char* ConfigManager::m_namespace = "esp32sense";
