#ifndef DETECTION_POSTPROCESS_H
#define DETECTION_POSTPROCESS_H

#include <cstdint>
#include <vector>

struct Detection {
    float x1, y1, x2, y2;  // Bounding box (absolute pixels)
    float confidence;        // Detection confidence [0, 1]
    int class_id;            // Class ID (0 = person)
};

class DetectionPostprocess {
public:
    DetectionPostprocess();

    /**
     * Post-process YOLOv8n output tensor.
     * @param output Raw model output (float array)
     * @param output_size Number of float values in output
     * @param input_width  Model input width (pixels)
     * @param input_height Model input height (pixels)
     * @param conf_threshold Confidence threshold
     * @param iou_threshold  NMS IoU threshold
     * @return Vector of filtered detections
     */
    std::vector<Detection> processYOLOv8(
        const float* output, int output_size,
        int input_width, int input_height,
        float conf_threshold = 0.25f,
        float iou_threshold = 0.5f
    );

    /**
     * Apply Non-Maximum Suppression.
     */
    std::vector<Detection> nms(
        const std::vector<Detection>& detections,
        float iou_threshold
    );

private:
    float iou(const Detection& a, const Detection& b) const;

    // YOLOv8n output structure:
    // [batch, 84, 8400] for 192x192 input
    // 84 = 4 (bbox) + 80 (COCO classes)
    // We filter for class 0 (person)
    static constexpr int kNumClasses = 80;
    static constexpr int kBboxOffset = 4;
};

#endif // DETECTION_POSTPROCESS_H
