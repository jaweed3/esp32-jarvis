#include "inference_engine.h"
#include "model_data.h"

#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/micro/kernels/micro_ops.h"

#include <Arduino.h>
#include "soc/timer_group_struct.h"
#include <esp_heap_caps.h>

static void feedWatchdog() {
    TIMERG0.wdtwprotect.val = 0x50D83AA1;
    TIMERG0.wdtfeed.val = 1;
    TIMERG0.wdtwprotect.val = 0;
    TIMERG1.wdtwprotect.val = 0x50D83AA1;
    TIMERG1.wdtfeed.val = 1;
    TIMERG1.wdtwprotect.val = 0;
}

static constexpr int kTensorArenaSize = 4 * 1024 * 1024;

static uint8_t* tensor_arena = nullptr;

static tflite::MicroMutableOpResolver<14> resolver;

static bool registerOps() {
  TfLiteStatus s;
  s = resolver.AddAdd();                   if (s != kTfLiteOk) { Serial.println("AddAdd FAILED"); return false; }
  s = resolver.AddConcatenation();         if (s != kTfLiteOk) { Serial.println("AddConcatenation FAILED"); return false; }
  s = resolver.AddConv2D();                if (s != kTfLiteOk) { Serial.println("AddConv2D FAILED"); return false; }
  s = resolver.AddLogistic();              if (s != kTfLiteOk) { Serial.println("AddLogistic FAILED"); return false; }
  s = resolver.AddMaxPool2D();             if (s != kTfLiteOk) { Serial.println("AddMaxPool2D FAILED"); return false; }
  s = resolver.AddMul();                   if (s != kTfLiteOk) { Serial.println("AddMul FAILED"); return false; }
  s = resolver.AddPad();                   if (s != kTfLiteOk) { Serial.println("AddPad FAILED"); return false; }
  s = resolver.AddQuantize();              if (s != kTfLiteOk) { Serial.println("AddQuantize FAILED"); return false; }
  s = resolver.AddReshape();               if (s != kTfLiteOk) { Serial.println("AddReshape FAILED"); return false; }
  s = resolver.AddResizeNearestNeighbor(); if (s != kTfLiteOk) { Serial.println("AddResizeNearestNeighbor FAILED"); return false; }
  s = resolver.AddSoftmax();               if (s != kTfLiteOk) { Serial.println("AddSoftmax FAILED"); return false; }
  s = resolver.AddStridedSlice();          if (s != kTfLiteOk) { Serial.println("AddStridedSlice FAILED"); return false; }
  s = resolver.AddSub();                   if (s != kTfLiteOk) { Serial.println("AddSub FAILED"); return false; }
  s = resolver.AddTranspose();             if (s != kTfLiteOk) { Serial.println("AddTranspose FAILED"); return false; }
  Serial.println("All ops registered OK");
  return true;
}

InferenceEngine::InferenceEngine() {}

InferenceEngine::~InferenceEngine() {
  delete static_cast<tflite::MicroInterpreter*>(m_interpreter);
}

bool InferenceEngine::begin() {
  feedWatchdog();
  tflite::InitializeTarget();

  Serial.print("Model size: ");
  Serial.print(model_tflite_len);
  Serial.println(" bytes");

  if (!registerOps()) return false;

  const tflite::Model* model = tflite::GetModel(model_tflite);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.print("Model schema version mismatch: got ");
    Serial.print(model->version());
    Serial.print(", expected ");
    Serial.println(TFLITE_SCHEMA_VERSION);
    return false;
  }
  Serial.println("Model loaded OK");

  tensor_arena = (uint8_t*)heap_caps_malloc(kTensorArenaSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!tensor_arena) {
    Serial.println("FATAL: Cannot allocate tensor arena in PSRAM");
    return false;
  }
  Serial.printf("Tensor arena: %d bytes in PSRAM\n", kTensorArenaSize);

  Serial.println("Creating interpreter...");
  m_interpreter = new tflite::MicroInterpreter(model, resolver, tensor_arena, kTensorArenaSize);
  if (!m_interpreter) {
    Serial.println("Interpreter creation FAILED");
    return false;
  }
  Serial.println("Allocating tensors...");
  feedWatchdog();
  Serial.printf("Free heap: %d  Free psram: %d  Arena: %d  Model: %d\n",
      ESP.getFreeHeap(), ESP.getFreePsram(), kTensorArenaSize, model_tflite_len);
  TfLiteStatus allocate_status = static_cast<tflite::MicroInterpreter*>(m_interpreter)->AllocateTensors();
  feedWatchdog();
  if (allocate_status != kTfLiteOk) {
    Serial.println("Tensor allocation FAILED");
    Serial.print("Arena used (so far): ");
    Serial.print(static_cast<tflite::MicroInterpreter*>(m_interpreter)->arena_used_bytes());
    Serial.print(" / ");
    Serial.println(kTensorArenaSize);
    return false;
  }
  Serial.println("Tensors allocated OK");
  Serial.print("Arena used: ");
  Serial.print(static_cast<tflite::MicroInterpreter*>(m_interpreter)->arena_used_bytes());
  Serial.print(" / ");
  Serial.print(kTensorArenaSize);
  Serial.println(" bytes");

  TfLiteTensor* input = static_cast<tflite::MicroInterpreter*>(m_interpreter)->input(0);
  TfLiteTensor* output = static_cast<tflite::MicroInterpreter*>(m_interpreter)->output(0);

  m_input_width = input->dims->data[2];
  m_input_height = input->dims->data[1];
  m_input_channels = input->dims->data[3];
  m_output_size = output->bytes / sizeof(int8_t);

  m_input_buffer = input->data.uint8;
  m_output_buffer_int8 = output->data.int8;

  Serial.print("  Output shape: [");
  for (int d = 0; d < output->dims->size; d++) {
    if (d) Serial.print(", ");
    Serial.print(output->dims->data[d]);
  }
  Serial.println("]");

  Serial.print("Tensor arena used: ");
  Serial.print(static_cast<tflite::MicroInterpreter*>(m_interpreter)->arena_used_bytes());
  Serial.print(" / ");
  Serial.print(kTensorArenaSize);
  Serial.println(" bytes");

  printModelInfo();
  m_fps_last_reset = millis();
  return true;
}

bool InferenceEngine::runInference(const uint8_t* input_data, int image_width, int image_height) {
  if (!m_interpreter || !m_input_buffer) return false;

  TfLiteTensor* input = static_cast<tflite::MicroInterpreter*>(m_interpreter)->input(0);

  float x_ratio = (float)image_width / m_input_width;
  float y_ratio = (float)image_height / m_input_height;

  int8_t* dst = reinterpret_cast<int8_t*>(m_input_buffer);
  for (int h = 0; h < m_input_height; h++) {
    int src_y = (int)(h * y_ratio);
    src_y = (src_y >= image_height) ? image_height - 1 : src_y;
    for (int w = 0; w < m_input_width; w++) {
      int src_x = (int)(w * x_ratio);
      src_x = (src_x >= image_width) ? image_width - 1 : src_x;
      int src_idx = (src_y * image_width + src_x) * 3;
      int dst_idx = (h * m_input_width + w) * 3;
      dst[dst_idx]     = (int8_t)((int)input_data[src_idx] - 128);
      dst[dst_idx + 1] = (int8_t)((int)input_data[src_idx + 1] - 128);
      dst[dst_idx + 2] = (int8_t)((int)input_data[src_idx + 2] - 128);
    }
  }

  unsigned long start = micros();
  TfLiteStatus status = static_cast<tflite::MicroInterpreter*>(m_interpreter)->Invoke();
  unsigned long elapsed = micros() - start;

  if (status != kTfLiteOk) {
    Serial.println("Inference FAILED");
    return false;
  }

  m_last_inference_us = elapsed;
  m_total_inference_us += elapsed;
  m_inference_count++;
  m_fps_counter++;
  return true;
}

int8_t* InferenceEngine::getOutputBuffer() { return m_output_buffer_int8; }
int InferenceEngine::getOutputSize() const { return m_output_size; }
int InferenceEngine::getInputWidth() const { return m_input_width; }
int InferenceEngine::getInputHeight() const { return m_input_height; }
int InferenceEngine::getInputChannels() const { return m_input_channels; }

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
  if (input->type == kTfLiteUInt8) Serial.println("UINT8");
  else if (input->type == kTfLiteInt8) Serial.println("INT8");
  else if (input->type == kTfLiteFloat32) Serial.println("FLOAT32");
  else Serial.println(input->type);
  if (input->quantization.type == kTfLiteAffineQuantization) {
    auto* quant = static_cast<TfLiteAffineQuantization*>(input->quantization.params);
    Serial.print("  Input scale: ");
    Serial.println(quant->scale->data[0], 6);
    Serial.print("  Input zero_point: ");
    Serial.println(quant->zero_point->data[0]);
  }
  TfLiteTensor* output = static_cast<tflite::MicroInterpreter*>(m_interpreter)->output(0);
  Serial.print("  Output type: ");
  if (output->type == kTfLiteUInt8) Serial.println("UINT8");
  else if (output->type == kTfLiteInt8) Serial.println("INT8");
  else if (output->type == kTfLiteFloat32) Serial.println("FLOAT32");
  else Serial.println(output->type);
  Serial.println("------------------");
}
