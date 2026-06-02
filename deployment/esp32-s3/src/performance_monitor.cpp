#include "performance_monitor.h"

PerformanceMonitor::PerformanceMonitor()
    : m_label("Benchmark")
    , m_frame_start_us(0)
    , m_total_inference_us(0)
    , m_min_inference_us(UINT32_MAX)
    , m_max_inference_us(0)
    , m_inference_count(0)
    , m_frame_count(0)
    , m_start_time_ms(0) {}

void PerformanceMonitor::begin(const char* label) {
    m_label = label;
    m_start_time_ms = millis();
    Serial.print("=== Performance Monitor: ");
    Serial.print(m_label);
    Serial.println(" ===");
    Serial.print("Free heap: ");
    Serial.print(getFreeHeap());
    Serial.print(" bytes, Free PSRAM: ");
    Serial.print(getFreePsram());
    Serial.println(" bytes");
}

void PerformanceMonitor::startFrame() {
    m_frame_start_us = micros();
}

void PerformanceMonitor::endFrame() {
    m_frame_count++;
}

void PerformanceMonitor::endInference(unsigned long inference_us) {
    m_inference_count++;
    m_total_inference_us += inference_us;
    if (inference_us < m_min_inference_us) m_min_inference_us = inference_us;
    if (inference_us > m_max_inference_us) m_max_inference_us = inference_us;
}

void PerformanceMonitor::printReport() {
    unsigned long elapsed_ms = millis() - m_start_time_ms;
    float elapsed_s = elapsed_ms / 1000.0f;

    Serial.println("\n=== Performance Report ===");
    Serial.print("Label: "); Serial.println(m_label);
    Serial.print("Runtime: "); Serial.print(elapsed_s); Serial.println(" s");
    Serial.print("Frames: "); Serial.println(m_frame_count);
    Serial.print("Inferences: "); Serial.println(m_inference_count);

    if (m_inference_count > 0) {
        float avg = m_total_inference_us / (float)m_inference_count / 1000.0f;
        float min_ms = m_min_inference_us / 1000.0f;
        float max_ms = m_max_inference_us / 1000.0f;

        Serial.print("Avg inference time: "); Serial.print(avg, 2); Serial.println(" ms");
        Serial.print("Min inference time: "); Serial.print(min_ms, 2); Serial.println(" ms");
        Serial.print("Max inference time: "); Serial.print(max_ms, 2); Serial.println(" ms");
        Serial.print("Total inference time: "); Serial.print(m_total_inference_us / 1000000.0f, 2); Serial.println(" s");
    }

    if (m_frame_count > 0) {
        Serial.print("Overall FPS: "); Serial.print(m_frame_count / elapsed_s, 1); Serial.println(" fps");
    }

    Serial.print("Free heap: "); Serial.print(getFreeHeap()); Serial.println(" bytes");
    Serial.print("Free PSRAM: "); Serial.print(getFreePsram()); Serial.println(" bytes");
    Serial.print("Inference CPU load: ");
    if (m_inference_count > 0) {
        float load = (m_total_inference_us / 1000000.0f) / elapsed_s * 100.0f;
        Serial.print(load, 1); Serial.println("%");
    } else {
        Serial.println("N/A");
    }
    Serial.println("========================\n");
}

void PerformanceMonitor::reset() {
    m_total_inference_us = 0;
    m_min_inference_us = UINT32_MAX;
    m_max_inference_us = 0;
    m_inference_count = 0;
    m_frame_count = 0;
    m_start_time_ms = millis();
}

float PerformanceMonitor::getFps() const {
    unsigned long elapsed = millis() - m_start_time_ms;
    if (elapsed == 0) return 0;
    return (float)m_frame_count / (elapsed / 1000.0f);
}

float PerformanceMonitor::getAvgInferenceTimeMs() const {
    if (m_inference_count == 0) return 0;
    return m_total_inference_us / (float)m_inference_count / 1000.0f;
}

float PerformanceMonitor::getMinInferenceTimeMs() const {
    return m_min_inference_us / 1000.0f;
}

float PerformanceMonitor::getMaxInferenceTimeMs() const {
    return m_max_inference_us / 1000.0f;
}

size_t PerformanceMonitor::getFreeHeap() const {
    return ESP.getFreeHeap();
}

size_t PerformanceMonitor::getFreePsram() const {
    return ESP.getFreePsram();
}
