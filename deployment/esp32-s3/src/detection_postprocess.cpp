#include "detection_postprocess.h"
#include <algorithm>
#include <cmath>
#include <Arduino.h>

DetectionPostprocess::DetectionPostprocess() {}

// YOLOv8n INT8 output: [1, 84, 756]
// Memory layout: channel-major (row-major for [ch, pred]):
//   cx[pred=0..755], cy[pred=0..755], w[pred=0..755], h[pred=0..755],
//   class0_score[pred=0..755], class1_score[pred=0..755], ...
// Dequantize: float = (int8_val - zero_point) * scale

std::vector<Detection> DetectionPostprocess::processYOLOv8(
    const int8_t* output, int output_size,
    int input_width, int input_height,
    float conf_threshold, float iou_threshold) {

    std::vector<Detection> detections;

    if (output_size < kNumPredictions * kStride) {
        Serial.print("Warning: unexpected output size: ");
        Serial.println(output_size);
        return detections;
    }

    for (int i = 0; i < kNumPredictions; i++) {
        float person_score = (output[4 * kNumPredictions + i] - kOutputZeroPoint) * kOutputScale;
        if (person_score < conf_threshold) continue;

        float cx = (output[0 * kNumPredictions + i] - kOutputZeroPoint) * kOutputScale;
        float cy = (output[1 * kNumPredictions + i] - kOutputZeroPoint) * kOutputScale;
        float w  = (output[2 * kNumPredictions + i] - kOutputZeroPoint) * kOutputScale;
        float h  = (output[3 * kNumPredictions + i] - kOutputZeroPoint) * kOutputScale;

        float x1 = (cx - w / 2.0f) * input_width;
        float y1 = (cy - h / 2.0f) * input_height;
        float x2 = (cx + w / 2.0f) * input_width;
        float y2 = (cy + h / 2.0f) * input_height;

        x1 = std::max(0.0f, std::min(x1, (float)input_width));
        y1 = std::max(0.0f, std::min(y1, (float)input_height));
        x2 = std::max(0.0f, std::min(x2, (float)input_width));
        y2 = std::max(0.0f, std::min(y2, (float)input_height));

        detections.push_back({x1, y1, x2, y2, person_score, 0});
    }

    return nms(detections, iou_threshold);
}

std::vector<Detection> DetectionPostprocess::nms(
    const std::vector<Detection>& detections,
    float iou_threshold) {

    if (detections.empty()) return {};

    std::vector<Detection> sorted = detections;
    std::sort(sorted.begin(), sorted.end(),
        [](const Detection& a, const Detection& b) {
            return a.confidence > b.confidence;
        });

    std::vector<Detection> result;
    std::vector<bool> suppressed(sorted.size(), false);

    for (size_t i = 0; i < sorted.size(); i++) {
        if (suppressed[i]) continue;
        result.push_back(sorted[i]);
        for (size_t j = i + 1; j < sorted.size(); j++) {
            if (suppressed[j]) continue;
            if (iou(sorted[i], sorted[j]) > iou_threshold) {
                suppressed[j] = true;
            }
        }
    }

    return result;
}

float DetectionPostprocess::iou(const Detection& a, const Detection& b) const {
    float x1 = std::max(a.x1, b.x1);
    float y1 = std::max(a.y1, b.y1);
    float x2 = std::min(a.x2, b.x2);
    float y2 = std::min(a.y2, b.y2);

    float inter_w = std::max(0.0f, x2 - x1);
    float inter_h = std::max(0.0f, y2 - y1);
    float inter_area = inter_w * inter_h;

    float area_a = (a.x2 - a.x1) * (a.y2 - a.y1);
    float area_b = (b.x2 - b.x1) * (b.y2 - b.y1);
    float union_area = area_a + area_b - inter_area;

    if (union_area <= 0.0f) return 0.0f;
    return inter_area / union_area;
}
