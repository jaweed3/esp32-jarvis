#include "esp_https_server.h"
#include "Arduino.h"
#include "esp_camera.h"
#include "WiFi.h"

const char* ssid = "MOVISTAR_6A18";
const char* password = "TYRYTVCJTYVKX4TbJYPY";

#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   10
#define SIOD_GPIO_NUM   40
#define SIOC_GPIO_NUM   39

#define Y9_GPIO_NUM     48
#define Y8_GPIO_NUM     11
#define Y7_GPIO_NUM     12
#define Y6_GPIO_NUM     14
#define Y5_GPIO_NUM     16
#define Y4_GPIO_NUM     18
#define Y3_GPIO_NUM     17
#define Y2_GPIO_NUM     15
#define VSYNC_GPIO_NUM  38
#define HREF_GPIO_NUM   47
#define PCLK_GPIO_NUM   13

// HTTP Server Logic
httpd_handle_t stream_httpd = NULL;

// Function for the Browser
static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t * _jpg_buf = NULL;
    char * part_buf[64];

    // Header MJPEG
}

void startCameraServer();

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();

    // checking the PSRAM
    if (psramFound()){
        Serial.println("PSRAM Found@ (Good, kita butuh ini untuk buffer video!)");
    } else {
        Serial.println("FATAL ERROR! PSRAM Not found. Enable OPI PSRAM do Tools!");
        return;
    }

    // camera config
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_UXGA;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 2;

    // Init camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x", err);
        return;
    }

    // decrease the frame size 
    sensor_t * s = esp_camera_sensor_get();
    if (s->id.PID == OV2640_PID) {
        s->set_framesize(s, FRAMESIZE_HVGA);
    } 

    // trying to connect to the wifi.
    WiFi.begin(ssid, password);
    WiFi.setSleep(false);

    Serial.print("WFi Connecting");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print("Try to connect...\n");
    }
    Serial.println("");
    Serial.println("Wifi Connected.");

    // Start Server
    Serial.print("Camera Ready! use 'http://");
    Serial.print(WiFi.localIP());
    Serial.println("' to Connect");
}

void loop() {
    delay(10000);
}   
