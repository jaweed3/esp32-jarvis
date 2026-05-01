#pragma once
#include <Arduino.h>
#include <map>

enum class DeviceState {
    INIT,
    AP_MODE,
    CONNECTING,
    IDLE,
    ACTIVE,
    ERROR
};

class StateMachine {
public:
    using Handler = std::function<void()>;

    void begin(DeviceState startState = DeviceState::INIT) {
        m_current = DeviceState::INIT;
        Serial.println("StateMachine: INIT");
    }

    void update() {
        // Check timeout
        if (m_timeout > 0 && millis() - m_enteredAt > m_timeout) {
            if (m_timeoutHandler) m_timeoutHandler();
            m_timeout = 0;
        }
    }

    void transitionTo(DeviceState newState) {
        if (newState == m_current) return;

        // Exit current
        auto exitIt = m_onExit.find(m_current);
        if (exitIt != m_onExit.end() && exitIt->second) exitIt->second();

        m_previous = m_current;
        m_current = newState;
        m_enteredAt = millis();
        m_timeout = 0; // reset timeout per state

        Serial.printf("StateMachine: %s -> %s\n",
                      stateName(m_previous), stateName(m_current));

        // Enter new
        auto enterIt = m_onEnter.find(m_current);
        if (enterIt != m_onEnter.end() && enterIt->second) enterIt->second();
    }

    DeviceState current() const { return m_current; }
    DeviceState previous() const { return m_previous; }

    unsigned long timeInState() const { return millis() - m_enteredAt; }

    void setTimeout(unsigned long ms) { m_timeout = ms; }
    void clearTimeout() { m_timeout = 0; }

    void onEnter(DeviceState state, Handler h) { m_onEnter[state] = h; }
    void onExit(DeviceState state, Handler h) { m_onExit[state] = h; }
    void onTimeout(Handler h) { m_timeoutHandler = h; }

    const char* stateName(DeviceState s) const {
        switch (s) {
            case DeviceState::INIT:       return "INIT";
            case DeviceState::AP_MODE:    return "AP_MODE";
            case DeviceState::CONNECTING: return "CONNECTING";
            case DeviceState::IDLE:       return "IDLE";
            case DeviceState::ACTIVE:     return "ACTIVE";
            case DeviceState::ERROR:      return "ERROR";
            default: return "UNKNOWN";
        }
    }

private:
    DeviceState m_current = DeviceState::INIT;
    DeviceState m_previous = DeviceState::INIT;
    unsigned long m_enteredAt = 0;
    unsigned long m_timeout = 0;
    Handler m_timeoutHandler = nullptr;

    std::map<DeviceState, Handler> m_onEnter;
    std::map<DeviceState, Handler> m_onExit;
};
