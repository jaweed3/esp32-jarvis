#include "inference_engine.h"
#include "model_data.h"

// TFLite Micro headers
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

// Include all needed ops
#include "tensorflow/lite/micro/kernels/micro_ops.h"
#include "tensorflow/lite/kernels/internal/reference/reference_ops.h"

// For conv2d and other common ops
#include "tensorflow/lite/micro/all_ops_resolver.h"

#include <Arduino.h>

static constexpr int kTensorArenaSize = 2 * 1024 * 1024;  // 2MB PSRAM

// Global arena in PSRAM (since internal SRAM is limited)
static uint8_t tensor_arena[kTensorArenaSize] __attribute__((section(".psram.data")));

// Op resolver (include all ops for YOLOv8n)
static tflite::AllOpsResolver resolver;

InferenceEngine::InferenceEngine() {}

InferenceEngine::~InferenceEngine() {
    delete static_cast<tflite::MicroInterpreter*>(m_interpreter);
}

bool InferenceEngine::begin() {
    tflite::InitializeTarget();

    Serial.print("Model size: ");
    Serial.print(model_tflite_len);
    Serial.println(" bytes");

    // Get model from compiled header
    const tflite::Model* model = tflite::GetModel(model_tflite);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.print("Model schema version mismatch: got ");
        Serial.print(model->version());
        Serial.print(", expected ");
        Serial.println(TFLITE_SCHEMA_VERSION);
        return false;
    }
    Serial.println("Model loaded OK");

    // Create interpreter
    m_interpreter = new tflite::MicroInterpreter(
        model, resolver, tensor_arena, kTensorArenaSize
    );

    TfLiteStatus allocate_status = static_cast<tflite::MicroInterpreter*>(m_interpreter)->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        Serial.println("Tensor allocation FAILED");
        return false;
    }
    Serial.println("Tensors allocated OK");

    // Get input/output details
    TfLiteTensor* input = static_cast<tflite::MicroInterpreter*>(m_interpreter)->input(0);
    TfLiteTensor* output = static_cast<tflite::MicroInterpreter*>(m_interpreter)->output(0);

    m_input_width = input->dims->data[2];
    m_input_height = input->dims->data[1];
    m_input_channels = input->dims->data[3];
    m_output_size = output->bytes / sizeof(float);

    m_input_buffer = input->data.uint8;
    m_output_buffer = reinterpret_cast<float*>(output->data.data);

    // Print arena usage
    Serial.print("Tensor arena used: ");
    Serial.print(static_cast<tflite::MicroInterpreter*>(m_interpreter)->arena_used_bytes());
    Serial.print(" / ");
    Serial.print(kTensorArenaSize);
    Serial.println(" bytes");

    // Print model info
    printModelInfo();

    m_fps_last_reset = millis();
    return true;
}

bool InferenceEngine::runInference(const uint8_t* input_data, int image_width, int image_height) {
    if (!m_interpreter || !m_input_buffer) {
        return false;
    }

    TfLiteTensor* input = static_cast<tflite::MicroInterpreter*>(m_interpreter)->input(0);

    // Preprocess: resize and convert RGB to model input format
    // The model takes uint8 [1, 192, 192, 3] with values [0, 255]
    // We resize from camera frame to model input size

    // Simple nearest-neighbor resize for speed (ESP32-S3 has no FPU for bilinear)
    float x_ratio = (float)image_width / m_input_width;
    float y_ratio = (float)image_height / m_input_height;

    // Direct resize with pixel sampling
    for (int h = 0; h < m_input_height; h++) {
        int src_y = (int)(h * y_ratio);
        src_y = (src_y >= image_height) ? image_height - 1 : src_y;

        for (int w = 0; w < m_input_width; w++) {
            int src_x = (int)(w * x_ratio);
            src_x = (src_x >= image_width) ? image_width - 1 : src_x;

            // Copy RGB pixel
            int src_idx = (src_y * image_width + src_x) * 3;
            int dst_idx = (h * m_input_width + w) * 3;
            m_input_buffer[dst_idx]     = input_data[src_idx];      // R
            m_input_buffer[dst_idx + 1] = input_data[src_idx + 1];  // G
            m_input_buffer[dst_idx + 2] = input_data[src_idx + 2];  // B
        }
    }

    // Run inference
    unsigned long start = micros();
    TfLiteStatus status = static_cast<tflite::MicroInterpreter*>(m_interpreter)->Invoke();
    unsigned long elapsed = micros() - start;

    if (status != kTfLiteOk) {
        Serial.println("Inference FAILED");
        return false;
    }

    // Update performance counters
    m_last_inference_us = elapsed;
    m_total_inference_us += elapsed;
    m_inference_count++;
    m_fps_counter++;

    return true;
}

float* InferenceEngine::getOutputBuffer() {
    return m_output_buffer;
}

int InferenceEngine::getOutputSize() const {
    return m_output_size;
}

int InferenceEngine::getInputWidth() const {
    return m_input_width;
}

int InferenceEngine::getInputHeight() const {
    return m_input_height;
}

int InferenceEngine::getInputChannels() const {
    return m_input_channels;
}

float InferenceEngine::getAverageInferenceTimeMs() const {
    if (m_inference_count == 0) return 0.0f;
    return (m_total_inference_us / (float)m_inference_count) / 1000.0f;
}

float InferenceEngine::getFps() const {
    unsigned long now = millis();
    unsigned long elapsed = now - m_fps_last_reset;
    if (elapsed == 0) return 0.0f;
    return (float)m_fps_counter / (elapsed / 1000.0f);
}

void InferenceEngine::printModelInfo() {
    Serial.println("--- Model Info ---");
    Serial.print("  Input shape: ");
    Serial.print(1); Serial.print("x");
    Serial.print(m_input_height); Serial.print("x");
    Serial.print(m_input_width); Serial.print("x");
    Serial.println(m_input_channels);

    Serial.print("  Output size: ");
    Serial.println(m_output_size);

    TfLiteTensor* input = static_cast<tflite::MicroInterpreter*>(m_interpreter)->input(0);
    Serial.print("  Input type: ");
    Serial.println(input->type == kTfLiteUInt8 ? "UINT8" : "FLOAT32");

    if (input->quantization.type == kTfLiteAffineQuantization) {
        auto* quant = static_cast<TfLiteAffineQuantization*>(input->quantization.params);
        Serial.print("  Input scale: ");
        Serial.println(quant->scale->data[0], 6);
        Serial.print("  Input zero_point: ");
        Serial.println(quant->zero_point->data[0]);
    }

    TfLiteTensor* output = static_cast<tflite::MicroInterpreter*>(m_interpreter)->output(0);
    Serial.print("  Output type: ");
    Serial.println(output->type == kTfLiteUInt8 ? "UINT8" : "FLOAT32");
    Serial.println("------------------");
}
