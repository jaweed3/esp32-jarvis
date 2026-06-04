#ifndef INFERENCE_ENGINE_H
#define INFERENCE_ENGINE_H

#include <cstddef>
#include <cstdint>

class InferenceEngine {
public:
    InferenceEngine();
    ~InferenceEngine();

    bool begin();
    bool runInference(const uint8_t* input_data, int image_width, int image_height);
    int8_t* getOutputBuffer();
    int getOutputSize() const;
    int getInputWidth() const;
    int getInputHeight() const;
    int getInputChannels() const;

    // Performance tracking
    unsigned long getLastInferenceTimeUs() const { return m_last_inference_us; }
    float getAverageInferenceTimeMs() const;
    float getFps() const;

    void printModelInfo();

private:
    void* m_interpreter = nullptr;
    void* m_tensor_arena = nullptr;
    size_t m_tensor_arena_size = 0;

    uint8_t* m_input_buffer = nullptr;
    int8_t* m_output_buffer_int8 = nullptr;

    int m_input_width = 192;
    int m_input_height = 192;
    int m_input_channels = 3;
    int m_output_size = 0;

    // Performance
    unsigned long m_last_inference_us = 0;
    unsigned long m_total_inference_us = 0;
    int m_inference_count = 0;
    int m_fps_counter = 0;
    unsigned long m_fps_last_reset = 0;
};

#endif // INFERENCE_ENGINE_H
