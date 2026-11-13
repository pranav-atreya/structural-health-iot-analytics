/*
 * ============================================================================
 * STRUCTURAL HEALTH IoT ANALYTICS — ESP32 INTEGRATED FIRMWARE
 * ============================================================================
 * Course:      Internet of Things (UE24CS342AA3) — PES University
 * Repository:  https://github.com/pranav-atreya/structural-health-iot-analytics
 * Team:
 *   - Pranav Shashikiran Atreya (PES2UG24CS912)
 *   - Yash Raghavendra A        (PES2UG24CS913)
 *   - Hemaksh Breja             (PES2UG24CS191)
 *   - Kashyap V P               (PES2UG24CS218)
 *
 * Active Hardware Channels (3 sensor groups — VL53L0X ToF officially dropped):
 *   1. IMU (GY-521 board, MPU-6050 / MPU-6500 register-level I2C driver):
 *      - SDA: GPIO 21, SCL: GPIO 22
 *      - Accepts WHO_AM_I = 0x68 (MPU-6050) and 0x70 (MPU-6500)
 *      - Reports actual WHO_AM_I value honestly in diagnostics and MQTT JSON
 *      - Configured for ~100 Hz sampling, +/-4g accel, +/-500 dps gyro, DLPF 0x03
 *      - Removes stationary gravity baseline via low-pass filter to compute
 *        dynamic vibration RMS (g) and peak dynamic vibration (g)
 *   2. Support-Reaction Load Cell (Sharvi 1 kg bar load cell + HX711):
 *      - DOUT/DT: GPIO 32, SCK: GPIO 33 (Bogdan Necula HX711 library)
 *      - Non-blocking conversion reads; preserves raw, tare-relative net, and
 *        EMA-filtered counts at all times
 *      - Exposes calibrated support reaction (`load_grams`) ONLY when a valid
 *        calibration factor (> 0.0) has been configured or calibrated
 *   3. Dual Digital IR Obstacle Modules (Vehicle Detection & Crossing State Machine):
 *      - IR1 OUT: GPIO 26, IR2 OUT: GPIO 27
 *      - Configurable active polarity (HIGH/LOW), per-sensor software debounce,
 *        transition counting, direction detection (1_to_2 vs 2_to_1), and
 *        optional speed estimation only when physical sensor spacing > 0.0 m
 *
 * Serial Interface (115200 baud):
 *   - Preserves the tested 10 Hz CSV format:
 *     time_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx_raw,hx_net,hx_filtered,ir1,ir2
 *   - Interactive commands:
 *     'T' or 't'          : Tare load cell (zero offset at unloaded state)
 *     'C <grams>'         : Calibrate load cell with known mass in grams
 *     'U' or 'u'          : Clear calibration factor back to uncalibrated mode
 *     'R' or 'r'          : Reset IR event and vehicle crossing counters
 *     'M' or 'm'          : Cycle Serial output mode (CSV only / JSON only / Both)
 *     'S' or 's'          : Print diagnostic status summary
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>
#include "HX711.h"

#if defined(__has_include)
  #if __has_include("secrets.h")
    #include "secrets.h"
    #define USING_LOCAL_SECRETS 1
  #else
    #include "secrets.example.h"
    #define USING_LOCAL_SECRETS 0
  #endif
#else
  #include "secrets.example.h"
  #define USING_LOCAL_SECRETS 0
#endif

// ==========================================
// PIN CONFIGURATION (LOCKED TO TESTED HARDWARE)
// ==========================================

#define SDA_PIN 21
#define SCL_PIN 22

#define IR1_PIN 26
#define IR2_PIN 27

#define HX_DT  32
#define HX_SCK 33

// ==========================================
// IMU (MPU-6050 / MPU-6500 LOW-LEVEL I2C)
// ==========================================

uint8_t mpuAddress = 0;
uint8_t imuWhoAmI  = 0;
bool mpuReady      = false;

int16_t mpuData[7] = {0};

// Latest scaled readings
float latestAxG   = 0.0f;
float latestAyG   = 0.0f;
float latestAzG   = 0.0f;
float latestGxDps = 0.0f;
float latestGyDps = 0.0f;
float latestGzDps = 0.0f;

// Gravity baseline removal (low-pass filter at 100 Hz, alpha = 0.02 -> ~0.32 Hz cutoff)
bool gravityBaselineSeeded = false;
float baselineAxG = 0.0f;
float baselineAyG = 0.0f;
float baselineAzG = 1.0f;
const float GRAVITY_LPF_ALPHA = 0.02f;

// Windowed dynamic vibration accumulators (for 1 Hz feature window)
double vibWindowSumSqG = 0.0;
float  vibWindowPeakG  = 0.0f;
uint32_t vibWindowCount = 0;

// Latest completed window features
float latestVibrationRmsG  = 0.0f;
float latestVibrationPeakG = 0.0f;

bool readRegister(uint8_t address, uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(address);
  Wire.write(reg);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(address, (uint8_t)1) != 1) {
    return false;
  }

  value = Wire.read();
  return true;
}

bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);

  return Wire.endTransmission() == 0;
}

bool initialiseMPU() {
  uint8_t identity = 0;

  if (readRegister(0x68, 0x75, identity)) {
    mpuAddress = 0x68;
  } else if (readRegister(0x69, 0x75, identity)) {
    mpuAddress = 0x69;
  } else {
    return false;
  }

  imuWhoAmI = identity;

  Serial.print("MPU address: 0x");
  Serial.println(mpuAddress, HEX);

  Serial.print("WHO_AM_I: 0x");
  Serial.println(identity, HEX);

  if (identity != 0x68 && identity != 0x70) {
    Serial.println("Unknown IMU identity!");
    return false;
  }

  Serial.println(
    identity == 0x70 ?
    "MPU-6500 DETECTED! (WHO_AM_I = 0x70)" :
    "MPU-6050 DETECTED! (WHO_AM_I = 0x68)"
  );

  // Wake up IMU (Power Management 1 register 0x6B)
  if (!writeRegister(mpuAddress, 0x6B, 0x00)) {
    return false;
  }

  delay(100);

  // Sample rate divider: 1 kHz / (1 + 9) = 100 Hz
  writeRegister(mpuAddress, 0x19, 9);

  // Digital low-pass filter: 0x03 (~44 Hz accel / ~42 Hz gyro bandwidth)
  writeRegister(mpuAddress, 0x1A, 0x03);

  // Gyroscope full-scale range: +/- 500 degrees/sec (65.5 LSB/dps)
  writeRegister(mpuAddress, 0x1B, 0x08);

  // Accelerometer full-scale range: +/- 4g (8192.0 LSB/g)
  writeRegister(mpuAddress, 0x1C, 0x08);

  return true;
}

bool readMPU() {
  Wire.beginTransmission(mpuAddress);
  Wire.write(0x3B);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(mpuAddress, (uint8_t)14) != 14) {
    return false;
  }

  for (int i = 0; i < 7; i++) {
    uint8_t highByte = Wire.read();
    uint8_t lowByte  = Wire.read();
    mpuData[i] = (int16_t)((highByte << 8) | lowByte);
  }

  latestAxG   = mpuData[0] / 8192.0f;
  latestAyG   = mpuData[1] / 8192.0f;
  latestAzG   = mpuData[2] / 8192.0f;
  latestGxDps = mpuData[4] / 65.5f;
  latestGyDps = mpuData[5] / 65.5f;
  latestGzDps = mpuData[6] / 65.5f;

  // Stationary gravity baseline tracking (exponential low-pass filter)
  if (!gravityBaselineSeeded) {
    baselineAxG = latestAxG;
    baselineAyG = latestAyG;
    baselineAzG = latestAzG;
    gravityBaselineSeeded = true;
  } else {
    baselineAxG = (1.0f - GRAVITY_LPF_ALPHA) * baselineAxG + GRAVITY_LPF_ALPHA * latestAxG;
    baselineAyG = (1.0f - GRAVITY_LPF_ALPHA) * baselineAyG + GRAVITY_LPF_ALPHA * latestAyG;
    baselineAzG = (1.0f - GRAVITY_LPF_ALPHA) * baselineAzG + GRAVITY_LPF_ALPHA * latestAzG;
  }

  // Dynamic vibration magnitude after removing quasi-static gravity vector
  float dynAx = latestAxG - baselineAxG;
  float dynAy = latestAyG - baselineAyG;
  float dynAz = latestAzG - baselineAzG;
  float dynMagG = sqrtf(dynAx * dynAx + dynAy * dynAy + dynAz * dynAz);

  vibWindowSumSqG += (double)(dynMagG * dynMagG);
  if (dynMagG > vibWindowPeakG) {
    vibWindowPeakG = dynMagG;
  }
  vibWindowCount++;

  // Continuously update rolling estimate so diagnostics always have fresh values
  latestVibrationRmsG  = (float)sqrt(vibWindowSumSqG / (double)vibWindowCount);
  latestVibrationPeakG = vibWindowPeakG;

  return true;
}

void finalizeVibrationWindow(float &rmsOut, float &peakOut) {
  if (vibWindowCount > 0) {
    rmsOut  = (float)sqrt(vibWindowSumSqG / (double)vibWindowCount);
    peakOut = vibWindowPeakG;
    latestVibrationRmsG  = rmsOut;
    latestVibrationPeakG = peakOut;
  } else {
    rmsOut  = latestVibrationRmsG;
    peakOut = latestVibrationPeakG;
  }
  vibWindowSumSqG = 0.0;
  vibWindowPeakG  = 0.0f;
  vibWindowCount  = 0;
}

// ==========================================
// HX711 LOAD CELL AMPLIFIER
// ==========================================

HX711 scale;

bool hxReady      = false;
bool hxHasReading = false;

long  hxZero     = 0;
long  hxRaw      = 0;
long  hxNet      = 0;
float hxFiltered = 0.0f;

float hxCalibrationFactor = HX711_CALIBRATION_FACTOR;

bool isLoadCellCalibrated() {
  return (hxCalibrationFactor > 0.0001f || hxCalibrationFactor < -0.0001f);
}

float getCalibratedSupportReactionGrams() {
  if (!isLoadCellCalibrated() || !hxHasReading) {
    return NAN;
  }
  return hxFiltered / hxCalibrationFactor;
}

void tareLoadCell() {
  if (!hxReady) {
    Serial.println("HX711 unavailable.");
    return;
  }

  Serial.println("\nTARE STARTED");
  Serial.println("Remove all additional load.");

  if (!scale.wait_ready_timeout(3000)) {
    Serial.println("HX711 NOT READY");
    return;
  }

  hxZero = scale.read_average(10);

  hxRaw      = hxZero;
  hxNet      = 0;
  hxFiltered = 0.0f;

  hxHasReading = true;

  Serial.print("New zero offset: ");
  Serial.println(hxZero);
  Serial.println("TARE COMPLETE\n");
}

void calibrateLoadCellWithKnownMass(float knownMassGrams) {
  if (!hxReady || !hxHasReading) {
    Serial.println("CALIBRATION_ERROR: HX711 not ready or no reading available.");
    return;
  }
  if (knownMassGrams <= 0.0f) {
    Serial.println("CALIBRATION_ERROR: Known reference mass must be > 0 grams.");
    return;
  }

  if (scale.wait_ready_timeout(2000)) {
    long avgRaw = scale.read_average(10);
    hxRaw      = avgRaw;
    hxNet      = avgRaw - hxZero;
    hxFiltered = (float)hxNet;
  }

  if (fabsf(hxFiltered) < 10.0f) {
    Serial.println("CALIBRATION_ERROR: Net counts too small. Place known mass on support after taring.");
    return;
  }

  hxCalibrationFactor = hxFiltered / knownMassGrams;
  Serial.println("\n======================================");
  Serial.println(" LOAD CELL CALIBRATION COMPLETE");
  Serial.println("======================================");
  Serial.print("Reference mass (g):      ");
  Serial.println(knownMassGrams, 2);
  Serial.print("Measured net counts:     ");
  Serial.println(hxFiltered, 2);
  Serial.print("Calibration factor:      ");
  Serial.print(hxCalibrationFactor, 4);
  Serial.println(" counts/g");
  Serial.println("NOTE: This represents support reaction at the instrumented support.");
  Serial.println("Copy this value to HX711_CALIBRATION_FACTOR in secrets.h to persist.");
  Serial.println("======================================\n");
}

// ==========================================
// IR SENSORS & VEHICLE CROSSING STATE MACHINE
// ==========================================

int irActiveState = IR_ACTIVE_STATE;

// Raw & debounced states
int rawIR1       = HIGH;
int rawIR2       = HIGH;
int debouncedIR1 = HIGH;
int debouncedIR2 = HIGH;
int previousIR1  = -1;
int previousIR2  = -1;

unsigned long lastIR1DebounceMs = 0;
unsigned long lastIR2DebounceMs = 0;

// Separate transition counters (incremented once per obstacle entry)
uint32_t ir1Events = 0;
uint32_t ir2Events = 0;

// Vehicle crossing state machine
enum CrossingState {
  CROSSING_IDLE = 0,
  CROSSING_1_TO_2_PENDING,
  CROSSING_2_TO_1_PENDING,
  CROSSING_WAIT_CLEAR
};

CrossingState crossingState      = CROSSING_IDLE;
unsigned long crossingStartMs    = 0;
unsigned long bothClearStartMs   = 0;
uint32_t      vehicleCount       = 0;
const char*   lastDirection      = "none";
unsigned long lastCrossingTimeMs = 0;
float         lastSpeedMps       = NAN;
float         irSensorSpacingM   = IR_SENSOR_SPACING_M;

bool isSensorBlocked(int pinLevel) {
  return (pinLevel == irActiveState);
}

void updateIRSensors(int ir1PinVal, int ir2PinVal) {
  unsigned long now = millis();

  // 1. Software debounce for IR1
  if (ir1PinVal != rawIR1) {
    rawIR1 = ir1PinVal;
    lastIR1DebounceMs = now;
  }
  bool ir1TransitionedActive = false;
  if ((now - lastIR1DebounceMs) >= IR_DEBOUNCE_MS) {
    if (previousIR1 == -1) {
      debouncedIR1 = rawIR1;
      previousIR1  = rawIR1;
    } else if (rawIR1 != debouncedIR1) {
      debouncedIR1 = rawIR1;
      previousIR1  = debouncedIR1;

      Serial.print("IR_EVENT,");
      Serial.print(now);
      Serial.print(",SENSOR_1,");
      Serial.println(debouncedIR1 == HIGH ? "HIGH" : "LOW");

      if (isSensorBlocked(debouncedIR1)) {
        ir1Events++;
        ir1TransitionedActive = true;
      }
    }
  }

  // 2. Software debounce for IR2
  if (ir2PinVal != rawIR2) {
    rawIR2 = ir2PinVal;
    lastIR2DebounceMs = now;
  }
  bool ir2TransitionedActive = false;
  if ((now - lastIR2DebounceMs) >= IR_DEBOUNCE_MS) {
    if (previousIR2 == -1) {
      debouncedIR2 = rawIR2;
      previousIR2  = rawIR2;
    } else if (rawIR2 != debouncedIR2) {
      debouncedIR2 = rawIR2;
      previousIR2  = debouncedIR2;

      Serial.print("IR_EVENT,");
      Serial.print(now);
      Serial.print(",SENSOR_2,");
      Serial.println(debouncedIR2 == HIGH ? "HIGH" : "LOW");

      if (isSensorBlocked(debouncedIR2)) {
        ir2Events++;
        ir2TransitionedActive = true;
      }
    }
  }

  bool s1Blocked = isSensorBlocked(debouncedIR1);
  bool s2Blocked = isSensorBlocked(debouncedIR2);

  // 3. Two-sensor vehicle crossing state machine
  switch (crossingState) {
    case CROSSING_IDLE:
      if (ir1TransitionedActive && !ir2TransitionedActive) {
        crossingState   = CROSSING_1_TO_2_PENDING;
        crossingStartMs = now;
      } else if (ir2TransitionedActive && !ir1TransitionedActive) {
        crossingState   = CROSSING_2_TO_1_PENDING;
        crossingStartMs = now;
      } else if (ir1TransitionedActive && ir2TransitionedActive) {
        // Simultaneous trigger (very fast pass)
        vehicleCount++;
        lastDirection      = "simultaneous";
        lastCrossingTimeMs = 1;
        lastSpeedMps       = NAN;
        crossingState      = CROSSING_WAIT_CLEAR;
        bothClearStartMs   = 0;
      }
      break;

    case CROSSING_1_TO_2_PENDING:
      if (ir2TransitionedActive || s2Blocked) {
        unsigned long dt = (now >= crossingStartMs) ? (now - crossingStartMs) : 0;
        vehicleCount++;
        lastDirection      = "1_to_2";
        lastCrossingTimeMs = dt;
        if (irSensorSpacingM > 0.0001f && dt > 0) {
          lastSpeedMps = irSensorSpacingM / ((float)dt / 1000.0f);
        } else {
          lastSpeedMps = NAN;
        }
        Serial.print("VEHICLE_CROSSING,count=");
        Serial.print(vehicleCount);
        Serial.print(",dir=1_to_2,dt_ms=");
        Serial.println(lastCrossingTimeMs);

        crossingState    = CROSSING_WAIT_CLEAR;
        bothClearStartMs = 0;
      } else if ((now - crossingStartMs) > CROSSING_TIMEOUT_MS) {
        // Timeout waiting for sensor 2 — return to idle without false crossing count
        crossingState = CROSSING_IDLE;
      }
      break;

    case CROSSING_2_TO_1_PENDING:
      if (ir1TransitionedActive || s1Blocked) {
        unsigned long dt = (now >= crossingStartMs) ? (now - crossingStartMs) : 0;
        vehicleCount++;
        lastDirection      = "2_to_1";
        lastCrossingTimeMs = dt;
        if (irSensorSpacingM > 0.0001f && dt > 0) {
          lastSpeedMps = irSensorSpacingM / ((float)dt / 1000.0f);
        } else {
          lastSpeedMps = NAN;
        }
        Serial.print("VEHICLE_CROSSING,count=");
        Serial.print(vehicleCount);
        Serial.print(",dir=2_to_1,dt_ms=");
        Serial.println(lastCrossingTimeMs);

        crossingState    = CROSSING_WAIT_CLEAR;
        bothClearStartMs = 0;
      } else if ((now - crossingStartMs) > CROSSING_TIMEOUT_MS) {
        crossingState = CROSSING_IDLE;
      }
      break;

    case CROSSING_WAIT_CLEAR:
      // Require both sensors to be unblocked continuously for CROSSING_CLEAR_HOLD_MS
      if (!s1Blocked && !s2Blocked) {
        if (bothClearStartMs == 0) {
          bothClearStartMs = now;
        } else if ((now - bothClearStartMs) >= CROSSING_CLEAR_HOLD_MS) {
          crossingState = CROSSING_IDLE;
        }
      } else {
        bothClearStartMs = 0;
      }
      break;
  }
}

// ==========================================
// WI-FI & MQTT TELEMETRY ENGINE (NON-BLOCKING)
// ==========================================

WiFiClient espWiFiClient;
PubSubClient mqttClient(espWiFiClient);

bool wifiConfigured = false;
unsigned long lastWiFiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
uint32_t telemetrySeq = 0;

String mqttTopicTelemetry;
String mqttClientId;

enum SerialOutputMode {
  SERIAL_MODE_CSV_ONLY = 0,
  SERIAL_MODE_JSON_ONLY = 1,
  SERIAL_MODE_CSV_AND_JSON = 2
};

SerialOutputMode serialOutputMode = SERIAL_MODE_CSV_ONLY;

bool isPlaceholderCredential(const char* val) {
  if (val == nullptr || strlen(val) == 0) {
    return true;
  }
  return (strncmp(val, "YOUR_", 5) == 0);
}

void initialiseNetwork() {
  mqttTopicTelemetry = String("structural-health/") + String(DEVICE_ID) + String("/telemetry");
  mqttClientId       = String(DEVICE_ID) + String("-") + String((uint32_t)(ESP.getEfuseMac() & 0xFFFF), HEX);

  mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
  mqttClient.setBufferSize(768);
  mqttClient.setKeepAlive(15);
  mqttClient.setSocketTimeout(2);

  if (isPlaceholderCredential(WIFI_SSID)) {
    wifiConfigured = false;
    Serial.println("[NET] WIFI_SSID is still placeholder ('YOUR_WIFI_SSID').");
    Serial.println("[NET] Running in standalone Serial CSV mode. Copy secrets.example.h -> secrets.h for Wi-Fi/MQTT.");
    return;
  }

  wifiConfigured = true;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWiFiAttemptMs = millis();

  Serial.print("[NET] Connecting to Wi-Fi SSID: ");
  Serial.println(WIFI_SSID);
}

void maintainNetworkNonBlocking() {
  if (!wifiConfigured) {
    return;
  }

  unsigned long now = millis();

  // Check Wi-Fi connection without blocking sensor loop
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWiFiAttemptMs >= 10000UL) {
      lastWiFiAttemptMs = now;
      Serial.println("[NET] Wi-Fi disconnected. Attempting non-blocking reconnect...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
    return;
  }

  // Wi-Fi is connected; maintain MQTT connection non-blockingly
  if (!mqttClient.connected()) {
    if (now - lastMqttAttemptMs >= 5000UL) {
      lastMqttAttemptMs = now;
      bool connected = false;
      if (strlen(MQTT_USERNAME) > 0 && !isPlaceholderCredential(MQTT_USERNAME)) {
        connected = mqttClient.connect(mqttClientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
      } else {
        connected = mqttClient.connect(mqttClientId.c_str());
      }

      if (connected) {
        Serial.print("[MQTT] Connected to broker ");
        Serial.print(MQTT_BROKER_HOST);
        Serial.print(":");
        Serial.print(MQTT_BROKER_PORT);
        Serial.print(" | Topic: ");
        Serial.println(mqttTopicTelemetry);
      } else {
        Serial.print("[MQTT] Connect failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" (sensor sampling continues normally)");
      }
    }
  } else {
    mqttClient.loop();
  }
}

void buildAndPublishJsonTelemetry() {
  float winRmsG  = 0.0f;
  float winPeakG = 0.0f;
  finalizeVibrationWindow(winRmsG, winPeakG);

  telemetrySeq++;
  unsigned long nowMs = millis();

  char loadGramsStr[24];
  if (isLoadCellCalibrated() && hxHasReading) {
    snprintf(loadGramsStr, sizeof(loadGramsStr), "%.2f", getCalibratedSupportReactionGrams());
  } else {
    snprintf(loadGramsStr, sizeof(loadGramsStr), "null");
  }

  char speedStr[24];
  if (!isnan(lastSpeedMps) && irSensorSpacingM > 0.0001f) {
    snprintf(speedStr, sizeof(speedStr), "%.3f", lastSpeedMps);
  } else {
    snprintf(speedStr, sizeof(speedStr), "null");
  }

  char payload[640];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"firmware_version\":\"%s\",\"seq\":%lu,\"uptime_ms\":%lu,"
    "\"imu_ready\":%s,\"imu_who_am_i\":%u,"
    "\"vibration_rms_g\":%.4f,\"vibration_peak_g\":%.4f,"
    "\"ax_g\":%.4f,\"ay_g\":%.4f,\"az_g\":%.4f,"
    "\"gx_dps\":%.3f,\"gy_dps\":%.3f,\"gz_dps\":%.3f,"
    "\"hx711_ready\":%s,\"hx711_calibrated\":%s,\"calibration_factor\":%.4f,"
    "\"hx711_raw_counts\":%ld,\"hx711_net_counts\":%ld,\"hx711_filtered_counts\":%.2f,"
    "\"load_grams\":%s,"
    "\"ir1_state\":%d,\"ir2_state\":%d,\"ir1_events\":%lu,\"ir2_events\":%lu,"
    "\"vehicle_count\":%lu,\"last_direction\":\"%s\",\"last_crossing_ms\":%lu,\"last_speed_mps\":%s}",
    DEVICE_ID,
    FIRMWARE_VERSION,
    (unsigned long)telemetrySeq,
    nowMs,
    mpuReady ? "true" : "false",
    (unsigned int)imuWhoAmI,
    winRmsG,
    winPeakG,
    latestAxG,
    latestAyG,
    latestAzG,
    latestGxDps,
    latestGyDps,
    latestGzDps,
    (hxReady && hxHasReading) ? "true" : "false",
    isLoadCellCalibrated() ? "true" : "false",
    hxCalibrationFactor,
    hxRaw,
    hxNet,
    hxFiltered,
    loadGramsStr,
    debouncedIR1,
    debouncedIR2,
    (unsigned long)ir1Events,
    (unsigned long)ir2Events,
    (unsigned long)vehicleCount,
    lastDirection,
    lastCrossingTimeMs,
    speedStr
  );

  if (serialOutputMode == SERIAL_MODE_JSON_ONLY || serialOutputMode == SERIAL_MODE_CSV_AND_JSON) {
    Serial.println(payload);
  }

  if (wifiConfigured && WiFi.status() == WL_CONNECTED && mqttClient.connected()) {
    bool ok = mqttClient.publish(mqttTopicTelemetry.c_str(), payload, false);
    if (!ok) {
      Serial.println("[MQTT] Publish failed (check buffer size / broker connection).");
    }
  }
}

void printStatusSummary() {
  Serial.println("\n======================================");
  Serial.println(" SYSTEM STATUS SUMMARY");
  Serial.println("======================================");
  Serial.print("Device ID:          "); Serial.println(DEVICE_ID);
  Serial.print("Uptime (ms):        "); Serial.println(millis());
  Serial.print("IMU Status:         "); Serial.print(mpuReady ? "ONLINE (WHO_AM_I=0x" : "FAILED (0x");
  Serial.print(imuWhoAmI, HEX); Serial.println(")");
  Serial.print("Vibration RMS (g):  "); Serial.println(latestVibrationRmsG, 4);
  Serial.print("Vibration Peak (g): "); Serial.println(latestVibrationPeakG, 4);
  Serial.print("HX711 Status:       "); Serial.println(hxReady ? "ONLINE" : "FAILED");
  Serial.print("HX711 Zero Offset:  "); Serial.println(hxZero);
  Serial.print("HX711 Filtered Cts: "); Serial.println(hxFiltered, 2);
  Serial.print("Calibrated Reaction:");
  if (isLoadCellCalibrated()) {
    Serial.print(" "); Serial.print(getCalibratedSupportReactionGrams(), 2);
    Serial.print(" g (factor="); Serial.print(hxCalibrationFactor, 4); Serial.println(" cts/g)");
  } else {
    Serial.println(" UNCALIBRATED (use 'C <grams>' with a known reference mass)");
  }
  Serial.print("IR1 / IR2 States:   "); Serial.print(debouncedIR1); Serial.print(" / "); Serial.println(debouncedIR2);
  Serial.print("IR1 / IR2 Events:   "); Serial.print(ir1Events); Serial.print(" / "); Serial.println(ir2Events);
  Serial.print("Vehicle Count:      "); Serial.print(vehicleCount);
  Serial.print(" (last dir: "); Serial.print(lastDirection); Serial.println(")");
  Serial.print("Wi-Fi Status:       ");
  if (!wifiConfigured) {
    Serial.println("UNCONFIGURED (Serial-only mode)");
  } else if (WiFi.status() == WL_CONNECTED) {
    Serial.print("CONNECTED (IP: "); Serial.print(WiFi.localIP()); Serial.println(")");
  } else {
    Serial.println("DISCONNECTED");
  }
  Serial.print("MQTT Status:        ");
  Serial.println(mqttClient.connected() ? "CONNECTED" : "DISCONNECTED");
  Serial.println("======================================\n");
}

void handleSerialCommands() {
  while (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      continue;
    }

    char cmd = line.charAt(0);
    if (cmd == 'T' || cmd == 't') {
      tareLoadCell();
    } else if (cmd == 'C' || cmd == 'c') {
      String arg = line.substring(1);
      arg.trim();
      float refGrams = arg.toFloat();
      calibrateLoadCellWithKnownMass(refGrams);
    } else if (cmd == 'U' || cmd == 'u') {
      hxCalibrationFactor = 0.0f;
      Serial.println("HX711 calibration cleared (reporting raw/net/filtered counts only).");
    } else if (cmd == 'R' || cmd == 'r') {
      ir1Events          = 0;
      ir2Events          = 0;
      vehicleCount       = 0;
      lastDirection      = "none";
      lastCrossingTimeMs = 0;
      lastSpeedMps       = NAN;
      crossingState      = CROSSING_IDLE;
      Serial.println("IR event and vehicle counters reset to 0.");
    } else if (cmd == 'M' || cmd == 'm') {
      serialOutputMode = (SerialOutputMode)(((int)serialOutputMode + 1) % 3);
      Serial.print("Serial output mode changed to: ");
      if (serialOutputMode == SERIAL_MODE_CSV_ONLY) {
        Serial.println("CSV_ONLY (10 Hz)");
      } else if (serialOutputMode == SERIAL_MODE_JSON_ONLY) {
        Serial.println("JSON_ONLY (1 Hz)");
      } else {
        Serial.println("CSV_AND_JSON");
      }
    } else if (cmd == 'S' || cmd == 's') {
      printStatusSummary();
    }
  }
}

// ==========================================
// SETUP
// ==========================================

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(30);
  delay(1500);

  Serial.println("\n======================================");
  Serial.println(" STRUCTURAL HEALTH IoT ANALYTICS");
  Serial.println(" INTEGRATED SENSOR & MQTT FIRMWARE");
  Serial.println("======================================");

  pinMode(IR1_PIN, INPUT);
  pinMode(IR2_PIN, INPUT);

  // Initialise I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  delay(200);

  // [1] IMU
  Serial.println("\n[1] INITIALISING IMU (MPU-6050 / MPU-6500)");
  mpuReady = initialiseMPU();
  Serial.println(mpuReady ? "IMU: ONLINE" : "IMU: FAILED");

  // [2] HX711
  Serial.println("\n[2] INITIALISING HX711 LOAD CELL");
  scale.begin(HX_DT, HX_SCK);
  hxReady = scale.wait_ready_timeout(5000);

  if (hxReady) {
    Serial.println("HX711: ONLINE");
    Serial.println("Keep the load cell unloaded for tare.");
    tareLoadCell();
  } else {
    Serial.println("HX711: FAILED");
  }

  // [3] IR modules
  Serial.println("\n[3] IR MODULES");
  rawIR1       = digitalRead(IR1_PIN);
  rawIR2       = digitalRead(IR2_PIN);
  debouncedIR1 = rawIR1;
  debouncedIR2 = rawIR2;
  previousIR1  = rawIR1;
  previousIR2  = rawIR2;

  Serial.print("IR 1 initial state (GPIO 26): ");
  Serial.println(previousIR1);
  Serial.print("IR 2 initial state (GPIO 27): ");
  Serial.println(previousIR2);

  // [4] Wi-Fi & MQTT (Non-blocking)
  Serial.println("\n[4] INITIALISING NETWORK / MQTT");
  initialiseNetwork();

  // Sensor summary
  Serial.println("\n======================================");
  Serial.println(" HARDWARE INITIALISATION SUMMARY");
  Serial.println("======================================");
  Serial.print("IMU:        ");
  Serial.println(mpuReady ? "PASS" : "FAIL");
  Serial.print("HX711:      ");
  Serial.println(hxReady ? "PASS" : "FAIL");
  Serial.println("IR modules: GPIO INPUTS ACTIVE");
  Serial.println("\nSerial Commands:");
  Serial.println("  T          = Tare load cell (no additional load)");
  Serial.println("  C <grams>  = Calibrate load cell with known reference mass");
  Serial.println("  U          = Reset load cell to uncalibrated mode");
  Serial.println("  R          = Reset IR / vehicle counters");
  Serial.println("  M          = Toggle Serial mode (CSV / JSON / Both)");
  Serial.println("  S          = Print status summary");
  Serial.println("======================================");

  Serial.println(
    "\ntime_ms,ax_g,ay_g,az_g,"
    "gx_dps,gy_dps,gz_dps,"
    "hx_raw,hx_net,hx_filtered,ir1,ir2"
  );
}

// ==========================================
// MAIN LOOP
// ==========================================

void loop() {
  // 1. Process non-blocking Serial commands
  handleSerialCommands();

  // 2. Read & debounce IR sensors continuously
  int ir1 = digitalRead(IR1_PIN);
  int ir2 = digitalRead(IR2_PIN);
  updateIRSensors(ir1, ir2);

  // 3. Read HX711 whenever a conversion is ready (non-blocking)
  if (hxReady && scale.is_ready()) {
    hxRaw = scale.read();
    hxNet = hxRaw - hxZero;

    if (!hxHasReading) {
      hxFiltered   = (float)hxNet;
      hxHasReading = true;
    } else {
      hxFiltered = 0.25f * (float)hxNet + 0.75f * hxFiltered;
    }
  }

  // 4. Refresh IMU at ~100 Hz (every 10,000 us)
  static unsigned long lastMPU = 0;
  if (mpuReady && (micros() - lastMPU >= 10000UL)) {
    lastMPU = micros();
    if (!readMPU()) {
      Serial.println("MPU_READ_ERROR");
    }
  }

  // 5. Maintain Wi-Fi & MQTT non-blockingly
  maintainNetworkNonBlocking();

  // 6. Print combined Serial CSV data at 10 Hz (preserves tested telemetry format)
  static unsigned long lastCsvOutput = 0;
  if (millis() - lastCsvOutput >= SERIAL_CSV_INTERVAL_MS) {
    lastCsvOutput = millis();

    if (serialOutputMode == SERIAL_MODE_CSV_ONLY || serialOutputMode == SERIAL_MODE_CSV_AND_JSON) {
      Serial.print(lastCsvOutput);
      Serial.print(",");

      if (mpuReady) {
        Serial.print(latestAxG, 4);
        Serial.print(",");
        Serial.print(latestAyG, 4);
        Serial.print(",");
        Serial.print(latestAzG, 4);
        Serial.print(",");
        Serial.print(latestGxDps, 3);
        Serial.print(",");
        Serial.print(latestGyDps, 3);
        Serial.print(",");
        Serial.print(latestGzDps, 3);
      } else {
        Serial.print("NA,NA,NA,NA,NA,NA");
      }

      Serial.print(",");

      if (hxReady && hxHasReading) {
        Serial.print(hxRaw);
        Serial.print(",");
        Serial.print(hxNet);
        Serial.print(",");
        Serial.print(hxFiltered, 2);
      } else {
        Serial.print("NA,NA,NA");
      }

      Serial.print(",");
      Serial.print(debouncedIR1);
      Serial.print(",");
      Serial.println(debouncedIR2);
    }
  }

  // 7. Publish 1 Hz JSON feature summary over MQTT (and Serial if JSON mode active)
  static unsigned long lastMqttPublish = 0;
  if (millis() - lastMqttPublish >= MQTT_PUBLISH_INTERVAL_MS) {
    lastMqttPublish = millis();
    buildAndPublishJsonTelemetry();
  }
}
