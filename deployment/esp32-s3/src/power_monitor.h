#ifndef POWER_MONITOR_H
#define POWER_MONITOR_H

#include <Arduino.h>
#include <cstdint>

/**
 * PowerMonitor — Measure ESP32-S3 power consumption.
 *
 * Two modes:
 *   1. INA219 I2C sensor (external) — real power measurement
 *   2. Estimate-only — based on CPU frequency, PSRAM access, peripherals
 *
 * Wiring (INA219):
 *   INA219 VCC → ESP32 3.3V
 *   INA219 GND → ESP32 GND
 *   INA219 SDA → ESP32 GPIO 6 (I2C SDA on XIAO)
 *   INA219 SCL → ESP32 GPIO 7 (I2C SCL on XIAO)
 *   INA219 V+ → USB 5V (before LDO, to measure total system power)
 *   INA219 V- → ESP32 5V input (after sense resistor)
 */

class PowerMonitor {
public:
    PowerMonitor();

    /** Initialize INA219 sensor on default I2C. Returns false if not found. */
    bool begin(int sda = 6, int scl = 7);

    /** Read instantaneous power from INA219. Returns mW. */
    float readPowerMW();

    /** Read bus voltage. Returns V. */
    float readBusVoltage();

    /** Read shunt current. Returns mA. */
    float readCurrentMA();

    /** Log current power state to serial as JSON. */
    void logPower();

    /** Estimate power from model (no INA219 needed). */
    struct PowerEstimate {
        float cpu_ma;
        float psram_ma;
        float camera_ma;
        float wifi_ma;
        float base_ma;
        float total_ma;
        float power_mw;  // chip power = total_ma * 3.3V
    };

    /** Estimate power based on current system state. */
    PowerEstimate estimate(bool camera_on, bool wifi_on, bool inference_active);

    /** Print power estimate to serial. */
    void printEstimate(const PowerEstimate& est);

    /** Get INA219 present flag. */
    bool hasINA219() const { return m_has_ina; }

private:
    bool m_has_ina = false;
    uint8_t m_i2c_addr = 0x40;  // INA219 default address

    // INA219 register addresses
    static constexpr uint8_t REG_CONFIG  = 0x00;
    static constexpr uint8_t REG_SHUNT   = 0x01;
    static constexpr uint8_t REG_BUS     = 0x02;
    static constexpr uint8_t REG_POWER   = 0x03;
    static constexpr uint8_t REG_CURRENT = 0x04;
    static constexpr uint8_t REG_CALIB   = 0x05;

    // Configuration: 32V range, ±320mA, 12-bit, continuous
    static constexpr uint16_t INA219_CONFIG_VAL = 0x399F;

    // Calibration for 0.1Ω shunt, ±3.2A range
    static constexpr uint16_t INA219_CALIB_VAL = 4096;

    uint16_t readRegister16(uint8_t reg);
    void writeRegister16(uint8_t reg, uint16_t value);
};

#endif // POWER_MONITOR_H
