#include "Arduino.h"
#include "WiFi.h"

const char* ssid = "MOVISTAR_6A18";
const char* password = "TYRYTVCJTYVKX4TbJYPY";

void initWifi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Connecting to Wifi....");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print("Trying to connect to WIFI....\n");
        delay(1000);
    }
    Serial.println();
    Serial.println(WiFi.localIP());
}

void setup() {
    Serial.begin(115200);
    
    // Set WiFi ke mode Station dan disconnect dari sisa koneksi sebelumnya
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    initWifi();
}

void loop() {

}


void searchWifi() {
    Serial.println("Sedang scan network...");

    // WiFi.scanNetworks akan mengembalikan jumlah network yang ditemukan
    int n = WiFi.scanNetworks();
    
    if (n == 0) {
        Serial.println("TIDAK ADA NETWORK DITEMUKAN!");
        Serial.println("--> Cek Antena? Cek konektor U.FL?");
    } else {
        Serial.print(n);
        Serial.println(" network ditemukan:");
        for (int i = 0; i < n; ++i) {
            // Print SSID dan Kekuatan Sinyal (RSSI)
            Serial.print(i + 1);
            Serial.print(": ");
            Serial.print(WiFi.SSID(i));
            Serial.print(" (");
            Serial.print(WiFi.RSSI(i));
            Serial.print(")");
            // Cek Enkripsi
            Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN)?" [OPEN]":" [SECURED]");
            delay(10);
        }
    }
    Serial.println("-----------------------");

    // Tunggu 5 detik sebelum scan lagi
    delay(5000);
}
