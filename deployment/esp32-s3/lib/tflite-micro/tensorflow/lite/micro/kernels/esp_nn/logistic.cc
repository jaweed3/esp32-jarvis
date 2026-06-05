#include "tensorflow/lite/micro/kernels/logistic.h"

#include "tensorflow/lite/c/builtin_op_data.h"
#include "tensorflow/lite/c/common.h"
#include "tensorflow/lite/kernels/internal/common.h"
#include "tensorflow/lite/kernels/internal/quantization_util.h"
#include "tensorflow/lite/kernels/internal/reference/integer_ops/logistic.h"
#include "tensorflow/lite/kernels/internal/reference/logistic.h"
#include "tensorflow/lite/kernels/internal/tensor_ctypes.h"
#include "tensorflow/lite/kernels/kernel_util.h"
#include "tensorflow/lite/kernels/op_macros.h"
#include "tensorflow/lite/micro/kernels/kernel_util.h"
#include "tensorflow/lite/micro/micro_log.h"

#include <esp_timer.h>

#if ESP_NN
#include <esp_nn.h>
#endif

long long logistic_total_time = 0;

namespace tflite {
namespace {

struct NodeData {
  OpDataLogistic op_data;
#if ESP_NN
  int buffer_idx;
  float input_scale;
  int32_t input_zero_point;
  bool lut_prepared;
#endif
};

void* Init(TfLiteContext* context, const char* buffer, size_t length) {
  TFLITE_DCHECK(context->AllocatePersistentBuffer != nullptr);
  return context->AllocatePersistentBuffer(context, sizeof(NodeData));
}

TfLiteStatus Prepare(TfLiteContext* context, TfLiteNode* node) {
  MicroContext* micro_context = GetMicroContext(context);

  TFLITE_DCHECK(node->user_data != nullptr);
  NodeData* data = static_cast<NodeData*>(node->user_data);

  TF_LITE_ENSURE_EQ(context, NumInputs(node), 1);
  TF_LITE_ENSURE_EQ(context, NumOutputs(node), 1);

  TfLiteTensor* input = micro_context->AllocateTempInputTensor(node, 0);
  TF_LITE_ENSURE(context, input != nullptr);

  TF_LITE_ENSURE_STATUS(CalculateArithmeticOpDataLogistic(context, node, &data->op_data));

#if ESP_NN
  if (input->type == kTfLiteInt8) {
    data->buffer_idx = -1;
    data->input_scale = input->params.scale;
    data->input_zero_point = input->params.zero_point;
    data->lut_prepared = false;
    int scratch_buf_size = esp_nn_get_logistic_s8_scratch_size();
    if (scratch_buf_size > 0) {
      TF_LITE_ENSURE_STATUS(context->RequestScratchBufferInArena(
        context, scratch_buf_size, &data->buffer_idx));
    }
  }
#endif

  micro_context->DeallocateTempTfLiteTensor(input);
  return kTfLiteOk;
}

TfLiteStatus Eval(TfLiteContext* context, TfLiteNode* node) {
  const TfLiteEvalTensor* input =
      tflite::micro::GetEvalInput(context, node, kLogisticInputTensor);
  TfLiteEvalTensor* output =
      tflite::micro::GetEvalOutput(context, node, kLogisticOutputTensor);

  TFLITE_DCHECK(node->user_data != nullptr);
  NodeData* data = static_cast<NodeData*>(node->user_data);

  long long start_time = esp_timer_get_time();

  if (input->type == kTfLiteFloat32) {
    switch (output->type) {
      case kTfLiteFloat32: {
        reference_ops::Logistic(tflite::micro::GetTensorShape(input),
                                tflite::micro::GetTensorData<float>(input),
                                tflite::micro::GetTensorShape(output),
                                tflite::micro::GetTensorData<float>(output));
        break;
      }
      default:
        MicroPrintf("Input %s, output %s not supported.",
                    TfLiteTypeGetName(input->type),
                    TfLiteTypeGetName(output->type));
        return kTfLiteError;
    }
  } else if (input->type == kTfLiteInt16) {
    switch (output->type) {
      case kTfLiteInt16: {
        reference_integer_ops::Logistic(
            data->op_data.input_multiplier, data->op_data.input_left_shift,
            NumElements(input->dims),
            tflite::micro::GetTensorData<int16_t>(input),
            tflite::micro::GetTensorData<int16_t>(output));
        break;
      }
      default:
        MicroPrintf("Input %s, output %s not supported.",
                    TfLiteTypeGetName(input->type),
                    TfLiteTypeGetName(output->type));
        return kTfLiteError;
    }
  } else if (input->type == kTfLiteInt8) {
    switch (output->type) {
      case kTfLiteInt8: {
#if ESP_NN
        int8_t* lut = nullptr;
        if (data->buffer_idx > -1) {
          lut = static_cast<int8_t*>(context->GetScratchBuffer(context, data->buffer_idx));
          if (!data->lut_prepared) {
            esp_nn_logistic_s8_prepare(lut, data->input_zero_point, data->input_scale);
            data->lut_prepared = true;
          }
        }
        if (lut != nullptr) {
          int size = NumElements(input->dims);
          esp_nn_logistic_s8(
              tflite::micro::GetTensorData<int8_t>(input),
              tflite::micro::GetTensorData<int8_t>(output),
              size, lut);
        } else {
          reference_integer_ops::Logistic(
              data->op_data.input_zero_point, data->op_data.input_range_radius,
              data->op_data.input_multiplier, data->op_data.input_left_shift,
              NumElements(input->dims),
              tflite::micro::GetTensorData<int8_t>(input),
              tflite::micro::GetTensorData<int8_t>(output));
        }
#else
        reference_integer_ops::Logistic(
            data->op_data.input_zero_point, data->op_data.input_range_radius,
            data->op_data.input_multiplier, data->op_data.input_left_shift,
            NumElements(input->dims),
            tflite::micro::GetTensorData<int8_t>(input),
            tflite::micro::GetTensorData<int8_t>(output));
#endif
        break;
      }
      default:
        MicroPrintf("Input %s, output %s not supported.",
                    TfLiteTypeGetName(input->type),
                    TfLiteTypeGetName(output->type));
        return kTfLiteError;
    }
  } else {
    MicroPrintf("Input %s, output %s not supported.",
                TfLiteTypeGetName(input->type),
                TfLiteTypeGetName(output->type));
    return kTfLiteError;
  }

  logistic_total_time += esp_timer_get_time() - start_time;
  return kTfLiteOk;
}

}  // namespace

TFLMRegistration Register_LOGISTIC() {
  return tflite::micro::RegisterOp(Init, Prepare, Eval);
}

}  // namespace tflite
