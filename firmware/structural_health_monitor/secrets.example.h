#ifndef SECRETS_EXAMPLE_H
#define SECRETS_EXAMPLE_H

// ============================================================================
// STRUCTURAL HEALTH IoT ANALYTICS — CONFIGURATION TEMPLATE
// ============================================================================
// Copy this file to `secrets.h` in the same folder before flashing if you want
// Wi-Fi and MQTT publishing enabled with your local network credentials.
// `secrets.h` is ignored by Git (.gitignore) so credentials are never committed.
//
// NOTE: The firmware compiles and runs in Serial CSV diagnostic mode even if
// `secrets.h` is not created or if Wi-Fi/MQTT is unreachable.
// ============================================================================

// 1. Wi-Fi Credentials (2.4 GHz network required for ESP32)
#define WIFI_SSID           "Sybau"
#define WIFI_PASSWORD       "03122016praN"

// 2. MQTT Broker Configuration
// Run `ipconfig` (or `./scripts/setup.ps1`) on the Windows laptop running Docker
// and enter the laptop's Wi-Fi LAN IPv4 address below (e.g., "10.26.61.65").
// Do NOT use "localhost" or "mosquitto" here because this runs on the ESP32.
#define MQTT_BROKER_HOST    "10.26.61.65"
#define MQTT_BROKER_PORT    1883
#define MQTT_USERNAME       "bridge_iot"
#define MQTT_PASSWORD       "bridge_iot_pass"

// 3. Device Identification
#define DEVICE_ID           "esp32-bridge-01"
#define FIRMWARE_VERSION    "2.0.0"

// 4. HX711 Load-Cell Calibration
// Preliminary observation with an ~50 g bottle gave ~12,830 counts (~256.6 counts/g),
// which is ONLY a rough observation and NOT a validated calibration factor.
// Leave HX711_CALIBRATION_FACTOR as 0.0f until you perform a proper calibration
// using a known reference mass (via Serial command `C <grams>` or `calibrate_load_cell.py`).
// When 0.0f, the firmware reports raw/net/filtered counts and sets `load_grams` to null.
#define HX711_CALIBRATION_FACTOR  0.0f

// 5. IR Obstacle Sensor Configuration
// Standard LM393 digital IR obstacle modules output LOW (0) when an obstacle/car
// blocks/reflects the beam, and HIGH (1) when clear. Set to HIGH if using active-HIGH modules.
#define IR_ACTIVE_STATE           LOW
#define IR_DEBOUNCE_MS            25UL
#define CROSSING_TIMEOUT_MS       5000UL
#define CROSSING_CLEAR_HOLD_MS    150UL

// Distance between IR Sensor 1 (GPIO 26) and IR Sensor 2 (GPIO 27) in metres.
// Keep at 0.0f until physically measured on the bridge deck with a ruler.
// Speed (m/s) is calculated ONLY when IR_SENSOR_SPACING_M > 0.0f.
#define IR_SENSOR_SPACING_M       0.0f

// 6. Telemetry Reporting Rates
#define SERIAL_CSV_INTERVAL_MS    100UL   // 10 Hz serial CSV stream
#define MQTT_PUBLISH_INTERVAL_MS  1000UL  // 1 Hz MQTT JSON feature packet

#endif // SECRETS_EXAMPLE_H
