#include "power_monitor.h"
#include <Wire.h>

PowerMonitor::PowerMonitor() {}

bool PowerMonitor::begin(int sda, int scl) {
    Wire.begin(sda, scl);
    delay(10);

    // Probe INA219
    Wire.beginTransmission(m_i2c_addr);
    if (Wire.endTransmission() != 0) {
        Serial.println("PowerMonitor: INA219 not found (I2C probe failed). "
                       "Using estimation mode.");
        m_has_ina = false;
        return false;
    }

    // Configure INA219
    writeRegister16(REG_CONFIG, INA219_CONFIG_VAL);
    writeRegister16(REG_CALIB, INA219_CALIB_VAL);
    delay(1);

    m_has_ina = true;
    Serial.println("PowerMonitor: INA219 initialized OK");
    return true;
}

float PowerMonitor::readPowerMW() {
    if (!m_has_ina) return 0.0f;
    uint16_t raw = readRegister16(REG_POWER);
    return raw * 0.2f;  // mW per LSB (per datasheet with our calibration)
}

float PowerMonitor::readBusVoltage() {
    if (!m_has_ina) return 0.0f;
    uint16_t raw = readRegister16(REG_BUS);
    return (raw >> 3) * 4.0f / 1000.0f;  // mV → V
}

float PowerMonitor::readCurrentMA() {
    if (!m_has_ina) return 0.0f;
    uint16_t raw = readRegister16(REG_CURRENT);
    return (int16_t)raw * 0.1f;  // mA per LSB (with our calibration)
}

void PowerMonitor::logPower() {
    if (!m_has_ina) return;
    float v = readBusVoltage();
    float i = readCurrentMA();
    float p = readPowerMW();
    Serial.print("INA219: V=");
    Serial.print(v, 2);
    Serial.print("V I=");
    Serial.print(i, 3);
    Serial.print("A P=");
    Serial.print(p, 1);
    Serial.println("mW");
}

PowerMonitor::PowerEstimate PowerMonitor::estimate(
    bool camera_on, bool wifi_on, bool inference_active) {

    PowerEstimate est = {0, 0, 0, 0, 25, 0, 0};  // base = 25mA

    est.cpu_ma = inference_active ? 70.0f : 45.0f;
    est.psram_ma = (inference_active || camera_on) ? 20.0f : 5.0f;
    est.camera_ma = camera_on ? 50.0f : 0.0f;
    est.wifi_ma = wifi_on ? 180.0f : 0.0f;

    est.total_ma = est.base_ma + est.cpu_ma + est.psram_ma
                   + est.camera_ma + est.wifi_ma;
    est.power_mw = est.total_ma * 3.3f;

    return est;
}

void PowerMonitor::printEstimate(const PowerEstimate& est) {
    Serial.println("--- Power Estimate ---");
    Serial.print("  CPU:         "); Serial.print(est.cpu_ma); Serial.println(" mA");
    Serial.print("  PSRAM:       "); Serial.print(est.psram_ma); Serial.println(" mA");
    Serial.print("  Camera:      "); Serial.print(est.camera_ma); Serial.println(" mA");
    Serial.print("  WiFi:        "); Serial.print(est.wifi_ma); Serial.println(" mA");
    Serial.print("  Base:        "); Serial.print(est.base_ma); Serial.println(" mA");
    Serial.print("  Total:       "); Serial.print(est.total_ma); Serial.println(" mA");
    Serial.print("  Power:       "); Serial.print(est.power_mw); Serial.println(" mW");
    Serial.println("----------------------");
}

uint16_t PowerMonitor::readRegister16(uint8_t reg) {
    Wire.beginTransmission(m_i2c_addr);
    Wire.write(reg);
    Wire.endTransmission();
    Wire.requestFrom(m_i2c_addr, (uint8_t)2);
    uint16_t value = Wire.read() << 8;
    value |= Wire.read();
    return value;
}

void PowerMonitor::writeRegister16(uint8_t reg, uint16_t value) {
    Wire.beginTransmission(m_i2c_addr);
    Wire.write(reg);
    Wire.write((value >> 8) & 0xFF);
    Wire.write(value & 0xFF);
    Wire.endTransmission();
}
