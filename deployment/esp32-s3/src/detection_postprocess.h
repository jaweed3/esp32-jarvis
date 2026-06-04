#ifndef DETECTION_POSTPROCESS_H
#define DETECTION_POSTPROCESS_H

#include <cstdint>
#include <vector>

struct Detection {
    float x1, y1, x2, y2;
    float confidence;
    int class_id;
};

class DetectionPostprocess {
public:
    DetectionPostprocess();

    std::vector<Detection> processYOLOv8(
        const int8_t* output, int output_size,
        int input_width, int input_height,
        float conf_threshold = 0.25f,
        float iou_threshold = 0.5f
    );

    std::vector<Detection> nms(
        const std::vector<Detection>& detections,
        float iou_threshold
    );

private:
    float iou(const Detection& a, const Detection& b) const;

    static constexpr int kNumClasses = 80;
    static constexpr int kBboxOffset = 4;
    static constexpr int kStride = 84;
    static constexpr int kNumPredictions = 756;
    static constexpr float kOutputScale = 0.005038812756538391f;
    static constexpr int kOutputZeroPoint = -128;
};

#endif
