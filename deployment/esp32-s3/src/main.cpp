/**
 * RescueVision Edge — ESP32-S3 Victim Detection Firmware
 *
 * Runs INT8 quantized YOLOv8n inference via TFLite Micro on camera frames.
 * Reports detection results and performance metrics over serial.
 *
 * Memory map:
 *   - Model weights:  ~2 MB (flash, compiled as C array)
 *   - Tensor arena:   2 MB (PSRAM)
 *   - Frame buffer:    ~150 KB (PSRAM) at 320x240 RGB888
 *   - Stack/other:    ~100 KB (SRAM)
 */

#include <Arduino.h>
#include "esp_camera.h"
#include <vector>

#include "inference_engine.h"
#include "detection_postprocess.h"
#include "performance_monitor.h"

// ============================================================
// Pin Configuration (XIAO ESP32S3 Sense)
// ============================================================
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    10
#define SIOD_GPIO_NUM    40
#define SIOC_GPIO_NUM    39
#define Y9_GPIO_NUM      48
#define Y8_GPIO_NUM      11
#define Y7_GPIO_NUM      12
#define Y6_GPIO_NUM      14
#define Y5_GPIO_NUM      16
#define Y4_GPIO_NUM      18
#define Y3_GPIO_NUM      17
#define Y2_GPIO_NUM      15
#define VSYNC_GPIO_NUM   38
#define HREF_GPIO_NUM    47
#define PCLK_GPIO_NUM    13

// ============================================================
// Configuration Constants
// ============================================================
static constexpr int kCameraWidth = 320;
static constexpr int kCameraHeight = 240;
static constexpr int kCameraQuality = 12;  // JPEG quality (not used in RGB mode)
static constexpr float kConfThreshold = 0.25f;
static constexpr float kIouThreshold = 0.5f;
static constexpr int kBenchmarkSeconds = 30;  // Run benchmark for 30 seconds
static constexpr int kPrintInterval = 5;      // Print results every N seconds

// ============================================================
// Global Objects
// ============================================================
InferenceEngine g_engine;
DetectionPostprocess g_postproc;
PerformanceMonitor g_perf;
static bool g_has_camera = false;
static bool g_has_model = false;

// ============================================================
// Camera Helpers
// ============================================================
static bool initCamera() {
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
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_RGB888;
    config.frame_size = FRAMESIZE_QVGA;  // 320x240
    config.jpeg_quality = kCameraQuality;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed: 0x%x\n", err);
        return false;
    }

    // Sensor config
    sensor_t* s = esp_camera_sensor_get();
    s->set_framesize(s, FRAMESIZE_QVGA);
    s->set_pixformat(s, PIXFORMAT_RGB888);
    s->set_quality(s, kCameraQuality);
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_hmirror(s, 0);
    s->set_vflip(s, 0);

    Serial.println("Camera initialized: QVGA (320x240) RGB888");
    return true;
}

static bool captureRgbFrame(uint8_t* out_buffer, size_t buffer_size) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        return false;
    }

    if (fb->format != PIXFORMAT_RGB888) {
        Serial.printf("Unexpected format: %d\n", fb->format);
        esp_camera_fb_return(fb);
        return false;
    }

    size_t copy_size = std::min(buffer_size, (size_t)(fb->width * fb->height * 3));
    memcpy(out_buffer, fb->buf, copy_size);
    esp_camera_fb_return(fb);
    return true;
}

// ============================================================
// Detection Result Formatting
// ============================================================
static void printDetectionResults(const std::vector<Detection>& detections,
                                   unsigned long inference_us) {
    Serial.print("{\"t\":");
    Serial.print(millis());
    Serial.print(",\"inference_us\":");
    Serial.print(inference_us);
    Serial.print(",\"detections\":[");
    for (size_t i = 0; i < detections.size(); i++) {
        if (i > 0) Serial.print(",");
        Serial.print("{\"x1\":");
        Serial.print((int)detections[i].x1);
        Serial.print(",\"y1\":");
        Serial.print((int)detections[i].y1);
        Serial.print(",\"x2\":");
        Serial.print((int)detections[i].x2);
        Serial.print(",\"y2\":");
        Serial.print((int)detections[i].y2);
        Serial.print(",\"conf\":");
        Serial.print(detections[i].confidence, 3);
        Serial.print(",\"class\":");
        Serial.print(detections[i].class_id);
        Serial.print("}");
    }
    Serial.println("]}");
}

// ============================================================
// RGB888 Frame Buffer (PSRAM for large allocations)
// ============================================================
static uint8_t* s_frame_buffer = nullptr;
static constexpr size_t kFrameBufferSize = kCameraWidth * kCameraHeight * 3;  // ~230KB

// ============================================================
// Setup
// ============================================================
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n\n=== RescueVision Edge — ESP32-S3 ===");
    Serial.println("Victim Detection with INT8 Quantized YOLOv8n\n");

    // System info
    Serial.print("Chip: "); Serial.println(ESP.getChipModel());
    Serial.print("CPU Freq: "); Serial.print(ESP.getCpuFreqMHz()); Serial.println(" MHz");
    Serial.print("Flash: "); Serial.print(ESP.getFlashChipSize() / 1024 / 1024); Serial.println(" MB");
    Serial.print("PSRAM: "); Serial.print(ESP.getPsramSize() / 1024 / 1024); Serial.println(" MB");
    Serial.print("Free PSRAM: "); Serial.print(ESP.getFreePsram() / 1024); Serial.println(" KB");

    // Allocate frame buffer in PSRAM
    s_frame_buffer = (uint8_t*)ps_malloc(kFrameBufferSize);
    if (!s_frame_buffer) {
        Serial.println("FATAL: Cannot allocate frame buffer in PSRAM");
        Serial.println("Falling back to DRAM...");
        s_frame_buffer = (uint8_t*)malloc(kFrameBufferSize);
        if (!s_frame_buffer) {
            Serial.println("FATAL: Cannot allocate frame buffer at all");
            return;
        }
    }
    Serial.printf("Frame buffer: %zu bytes\n", kFrameBufferSize);

    // Initialize camera
    g_has_camera = initCamera();
    if (!g_has_camera) {
        Serial.println("Camera init failed. Running in benchmark-only mode.");
    }

    // Initialize TFLite Micro inference engine
    g_has_model = g_engine.begin();
    if (!g_has_model) {
        Serial.println("Model init failed!");
        return;
    }

    // Start performance monitoring
    g_perf.begin("YOLOv8n INT8 @ 192x192");
    Serial.println("\nStarting inference loop...\n");
}

// ============================================================
// Main Loop
// ============================================================
void loop() {
    if (!g_has_model) {
        delay(1000);
        Serial.println("Waiting for model...");
        return;
    }

    g_perf.startFrame();

    // Capture frame
    if (g_has_camera) {
        if (!captureRgbFrame(s_frame_buffer, kFrameBufferSize)) {
            delay(10);
            return;
        }
    } else {
        // No camera: fill with synthetic gray image (benchmark mode)
        memset(s_frame_buffer, 128, kFrameBufferSize);
    }

    // Run inference
    bool ok = g_engine.runInference(s_frame_buffer, kCameraWidth, kCameraHeight);
    if (!ok) {
        Serial.println("Inference failed");
        delay(100);
        return;
    }

    unsigned long inference_us = g_engine.getLastInferenceTimeUs();
    g_perf.endInference(inference_us);

    // Post-process detections
    float* output = g_engine.getOutputBuffer();
    int output_size = g_engine.getOutputSize();

    std::vector<Detection> detections = g_postproc.processYOLOv8(
        output, output_size,
        g_engine.getInputWidth(),
        g_engine.getInputHeight(),
        kConfThreshold,
        kIouThreshold
    );

    g_perf.endFrame();

    // Print results
    printDetectionResults(detections, inference_us);

    // Periodic benchmark report
    static unsigned long last_report = 0;
    unsigned long now = millis();
    if (now - last_report >= kPrintInterval * 1000) {
        last_report = now;
        g_perf.printReport();
    }

    // Stop after benchmark duration (optional)
    if (now >= kBenchmarkSeconds * 1000UL) {
        Serial.println("\n=== BENCHMARK COMPLETE ===");
        g_perf.printReport();
        Serial.println("\nEntering deep sleep. Press reset to rerun.");
        esp_deep_sleep_start();
    }
}
