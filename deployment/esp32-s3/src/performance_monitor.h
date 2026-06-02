#ifndef PERFORMANCE_MONITOR_H
#define PERFORMANCE_MONITOR_H

#include <Arduino.h>
#include <cstdint>

class PerformanceMonitor {
public:
    PerformanceMonitor();

    void begin(const char* label = "Benchmark");
    void startFrame();
    void endFrame();
    void endInference(unsigned long inference_us);

    void printReport();
    void reset();

    // Getters
    float getFps() const;
    float getAvgInferenceTimeMs() const;
    float getMinInferenceTimeMs() const;
    float getMaxInferenceTimeMs() const;
    size_t getFreeHeap() const;
    size_t getFreePsram() const;

private:
    const char* m_label;
    unsigned long m_frame_start_us;
    unsigned long m_total_inference_us;
    unsigned long m_min_inference_us;
    unsigned long m_max_inference_us;
    int m_inference_count;
    int m_frame_count;
    unsigned long m_start_time_ms;
};

#endif // PERFORMANCE_MONITOR_H
