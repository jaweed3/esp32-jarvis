#pragma once
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

enum class SystemEvent : uint8_t {
    NONE = 0,

    // Audio
    WAKE_WORD_DETECTED,
    VOICE_ACTIVITY_START,
    VOICE_ACTIVITY_END,

    // Video
    FACE_DETECTED,
    FACE_RECOGNIZED,
    FACE_UNKNOWN,

    // Network
    WIFI_CONNECTED,
    WIFI_DISCONNECTED,

    // System
    STATE_CHANGE,
    ERROR_OCCURRED,

    // User commands
    ENROLL_FACE,
    DELETE_FACE,
    CAPTURE_PHOTO,
    START_STREAM,
    STOP_STREAM,
    SYSTEM_REBOOT
};

struct EventMessage {
    SystemEvent event = SystemEvent::NONE;
    int32_t data[4] = {}; // payload fleksibel
};

class EventBus {
public:
    bool begin(size_t queueSize = 32) {
        m_queue = xQueueCreate(queueSize, sizeof(EventMessage));
        return m_queue != nullptr;
    }

    bool post(const EventMessage& msg) {
        return xQueueSend(m_queue, &msg, 0) == pdTRUE;
    }

    bool postFromISR(const EventMessage& msg) {
        BaseType_t higherPriorityTaskWoken = pdFALSE;
        BaseType_t result = xQueueSendFromISR(m_queue, &msg, &higherPriorityTaskWoken);
        if (higherPriorityTaskWoken) portYIELD_FROM_ISR();
        return result == pdTRUE;
    }

    bool receive(EventMessage& msg, TickType_t timeout = 0) {
        return xQueueReceive(m_queue, &msg, timeout) == pdTRUE;
    }

    size_t pending() const {
        return uxQueueMessagesWaiting(m_queue);
    }

private:
    QueueHandle_t m_queue = nullptr;
};
