# ESP32 Firmware — Structural Health IoT Analytics

Owner under the internal working arrangement: **Pranav Shashikiran Atreya (PES2UG24CS912)**, with hardware assembly and sensor placement coordination from **Yash Raghavendra A (PES2UG24CS913)**.

## Sketches in `firmware/`

1. **`structural_health_monitor/structural_health_monitor.ino`** *(Primary Production Sketch)*
   - Full non-blocking sensor acquisition + edge feature extraction + Serial CSV output + Wi-Fi/MQTT JSON telemetry publisher.
2. **`hardware_compatibility_test/hardware_compatibility_test.ino`** *(Preserved Diagnostic Baseline)*
   - Original locally verified standalone hardware test sketch (100 Hz IMU, HX711 load-cell tare/filtering, dual IR obstacle sensors, 10 Hz Serial CSV stream).

---

## Active Hardware Channels & Pin Map

> **Important Scope Note:** The VL53L0X Time-of-Flight (ToF) sensor has been officially dropped from the prototype. There is no direct deflection (`deflection_mm`) sensor in the active hardware.

| Sensor Group | Module | ESP32 Pin | Notes |
|---|---|---|---|
| **IMU (Vibration)** | GY-521 (MPU-6050 / MPU-6500) | SDA = `GPIO 21`, SCL = `GPIO 22` | I²C @ 100 kHz; accepts `WHO_AM_I` = `0x68` and `0x70`; ~100 Hz sampling |
| **Support Reaction** | Sharvi 1 kg Bar Load Cell + HX711 | DT/DOUT = `GPIO 32`, SCK = `GPIO 33` | Powered at `3.3 V`; Red=E+, Black=E-, Green=A+, White=A- |
| **Vehicle Detection** | Digital IR Obstacle Sensor 1 & 2 | IR1 OUT = `GPIO 26`, IR2 OUT = `GPIO 27` | Configurable polarity (`LOW` active default), 25 ms debounce, directional state machine |

---

## Required Arduino IDE Libraries

Install the following via **Arduino IDE → Tools → Manage Libraries**:

1. **`HX711 Arduino Library`** by **Bogdan Necula (bogde)** (`#include "HX711.h"`)
2. **`PubSubClient`** by **Nick O'Leary** (`#include <PubSubClient.h>`)
3. Built-in ESP32 libraries (`Wire.h`, `WiFi.h` from the **`esp32` by Espressif Systems** board package)

> **Do NOT use `Adafruit_MPU6050`:** Our GY-521 module has returned `WHO_AM_I` values of both `0x68` and `0x70` during integrated testing. The firmware uses our proven direct I²C register implementation (`0x75`, `0x6B`, `0x19`, `0x1A`, `0x1B`, `0x1C`, `0x3B`) so both `0x68` and `0x70` work reliably, while recording the actual `imu_who_am_i` integer in diagnostics and MQTT payloads.

---

## Configuration (`secrets.h`)

1. Copy `firmware/structural_health_monitor/secrets.example.h` to `firmware/structural_health_monitor/secrets.h`:
   ```powershell
   Copy-Item firmware\structural_health_monitor\secrets.example.h firmware\structural_health_monitor\secrets.h
   ```
2. Edit `firmware/structural_health_monitor/secrets.h` and set:
   - `WIFI_SSID` and `WIFI_PASSWORD` (2.4 GHz Wi-Fi network)
   - `MQTT_BROKER_HOST`: Your Windows laptop's LAN IPv4 address (find via `ipconfig` or `./scripts/setup.ps1`)
   - `MQTT_USERNAME` and `MQTT_PASSWORD` (matching `.env`, default `bridge_iot` / `bridge_iot_pass`)
   - `HX711_CALIBRATION_FACTOR`: Leave at `0.0f` until calibrated with a known mass (`load_grams` will be reported as `null` while raw, tare-relative net, and filtered counts are always transmitted).
   - `IR_SENSOR_SPACING_M`: Leave at `0.0f` until the physical distance (in metres) between IR1 and IR2 is measured and entered.

---

## Serial Monitor Commands (`115200` baud)

While the ESP32 is connected over USB, open Serial Monitor at `115200` baud (newline ending) and send:

- `T` — Tare the load cell at unloaded baseline.
- `C <grams>` (e.g., `C 50.0`) — Calibrate the load cell while a known reference mass (in grams) is placed on the bridge support. Prints the computed `HX711_CALIBRATION_FACTOR` (`counts/g`).
- `U` — Clear calibration factor back to uncalibrated counts-only mode (`0.0f`).
- `R` — Reset IR event counters and vehicle crossing count to `0`.
- `M` — Cycle Serial output mode between:
  1. `CSV_ONLY` (10 Hz `time_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx_raw,hx_net,hx_filtered,ir1,ir2`)
  2. `JSON_ONLY` (1 Hz structured JSON matching MQTT payload)
  3. `CSV_AND_JSON`
- `S` — Print a full diagnostic summary of sensors, calibration state, Wi-Fi IP, and MQTT connection status.
