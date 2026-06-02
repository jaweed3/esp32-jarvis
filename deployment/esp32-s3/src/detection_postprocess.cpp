#include "detection_postprocess.h"
#include <algorithm>
#include <cmath>
#include <Arduino.h>

DetectionPostprocess::DetectionPostprocess() {}

std::vector<Detection> DetectionPostprocess::processYOLOv8(
    const float* output, int output_size,
    int input_width, int input_height,
    float conf_threshold, float iou_threshold) {

    std::vector<Detection> detections;

    // YOLOv8n output layout (for TFLite):
    // Shape: [1, 84, 8400] where 8400 = number of predictions
    // Each prediction: 4 bbox coords + 80 class scores
    const int num_predictions = 8400;
    const int stride = kNumClasses + kBboxOffset;  // 84

    // Validate output size
    if (output_size < num_predictions * stride) {
        Serial.print("Warning: unexpected output size: ");
        Serial.println(output_size);
        return detections;
    }

    // For each prediction grid cell
    for (int i = 0; i < num_predictions; i++) {
        // Class scores start at index 4
        const float* scores = output + i * stride + kBboxOffset;

        // Find best class score (we only care about person = class 0)
        float max_score = scores[0];
        int best_class = 0;

        // Optionally scan all 80 classes
        // For single-class detection, just use class 0
        for (int c = 1; c < kNumClasses; c++) {
            if (scores[c] > max_score) {
                max_score = scores[c];
                best_class = c;
            }
        }

        if (max_score < conf_threshold) continue;

        // Decode bbox: output is [cx, cy, w, h] normalized [0,1]
        const float* bbox = output + i * stride;
        float cx = bbox[0];
        float cy = bbox[1];
        float w  = bbox[2];
        float h  = bbox[3];

        // Convert to pixel coordinates [x1, y1, x2, y2]
        float x1 = (cx - w / 2.0f) * input_width;
        float y1 = (cy - h / 2.0f) * input_height;
        float x2 = (cx + w / 2.0f) * input_width;
        float y2 = (cy + h / 2.0f) * input_height;

        // Clamp to image bounds
        x1 = std::max(0.0f, std::min(x1, (float)input_width));
        y1 = std::max(0.0f, std::min(y1, (float)input_height));
        x2 = std::max(0.0f, std::min(x2, (float)input_width));
        y2 = std::max(0.0f, std::min(y2, (float)input_height));

        detections.push_back({x1, y1, x2, y2, max_score, best_class});
    }

    // Apply NMS
    return nms(detections, iou_threshold);
}

std::vector<Detection> DetectionPostprocess::nms(
    const std::vector<Detection>& detections,
    float iou_threshold) {

    if (detections.empty()) return {};

    // Sort by confidence descending
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
    // Intersection
    float x1 = std::max(a.x1, b.x1);
    float y1 = std::max(a.y1, b.y1);
    float x2 = std::min(a.x2, b.x2);
    float y2 = std::min(a.y2, b.y2);

    float inter_w = std::max(0.0f, x2 - x1);
    float inter_h = std::max(0.0f, y2 - y1);
    float inter_area = inter_w * inter_h;

    // Union
    float area_a = (a.x2 - a.x1) * (a.y2 - a.y1);
    float area_b = (b.x2 - b.x1) * (b.y2 - b.y1);
    float union_area = area_a + area_b - inter_area;

    if (union_area <= 0.0f) return 0.0f;

    return inter_area / union_area;
}
