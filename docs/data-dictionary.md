# Data Dictionary — Serial CSV, MQTT JSON, InfluxDB & Experimental CSV

> **Deprecated Field Notice:** `deflection_mm` (from the dropped VL53L0X ToF sensor) has been completely removed from all schemas.

---

## 1. Serial Diagnostic CSV Schema (10 Hz)

Printed by `structural_health_monitor.ino` at `115200` baud every 100 ms:

```text
time_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx_raw,hx_net,hx_filtered,ir1,ir2
```

| Column | Type | Unit | Description |
|---|---|---|---|
| `time_ms` | `uint32` | `ms` | ESP32 `millis()` uptime since boot |
| `ax_g`, `ay_g`, `az_g` | `float` | $g$ | 3-axis acceleration ($\pm 4\,g$ range, $8192\text{ LSB}/g$) |
| `gx_dps`, `gy_dps`, `gz_dps` | `float` | $^\circ/\text{s}$ | 3-axis angular rate ($\pm 500^\circ/\text{s}$ range, $65.5\text{ LSB}/(^\circ/\text{s})$) |
| `hx_raw` | `long` | counts | Raw 24-bit signed HX711 ADC reading |
| `hx_net` | `long` | counts | Tare-relative counts (`hx_raw - hxZero`) |
| `hx_filtered` | `float` | counts | Exponential moving average (`0.25 * hx_net + 0.75 * hx_filtered`) |
| `ir1`, `ir2` | `int` (`0`/`1`) | digital | Debounced GPIO logic state on `GPIO 26` and `GPIO 27` (`0` = blocked for active-LOW) |

---

## 2. MQTT JSON Telemetry Schema (1 Hz)

Published to topic `structural-health/<device_id>/telemetry`:

| JSON Key | Type | Unit | Nullable? | Description |
|---|---|---|---|---|
| `device_id` | `string` | — | No | Unique ESP32 identifier (default `"esp32-bridge-01"`) |
| `firmware_version` | `string` | — | No | Firmware release string (`"2.0.0"`) |
| `seq` | `int` | count | No | Monotonic packet sequence number since boot |
| `uptime_ms` | `int` | `ms` | No | Milliseconds since ESP32 boot |
| `imu_ready` | `bool` | — | No | `true` if IMU initialized on I²C |
| `imu_who_am_i` | `int` | byte | No | Raw `WHO_AM_I` (`0x75`) register value (`104` = `0x68`, `112` = `0x70`) |
| `vibration_rms_g` | `float` | $g$ | No | Windowed RMS of dynamic acceleration magnitude after gravity LPF removal |
| `vibration_peak_g` | `float` | $g$ | No | Maximum instantaneous dynamic acceleration magnitude in the 1 s window |
| `ax_g`, `ay_g`, `az_g` | `float` | $g$ | No | Latest 3-axis accelerometer components |
| `gx_dps`, `gy_dps`, `gz_dps` | `float` | $^\circ/\text{s}$ | No | Latest 3-axis gyroscope components |
| `hx711_ready` | `bool` | — | No | `true` if HX711 is online and has completed initial tare |
| `hx711_calibrated` | `bool` | — | No | `true` only when `calibration_factor != 0.0` |
| `calibration_factor` | `float` | $\text{counts}/g$ | No | Active calibration factor (`0.0` when uncalibrated) |
| `hx711_raw_counts` | `int` | counts | No | Raw HX711 ADC reading |
| `hx711_net_counts` | `int` | counts | No | Tare-relative net counts (`hx_raw - hxZero`) |
| `hx711_filtered_counts` | `float` | counts | No | EMA-filtered net counts |
| `load_grams` | `float` | $g$ | **Yes (`null`)** | Calibrated support reaction in grams (`null` when uncalibrated) |
| `ir1_state`, `ir2_state` | `int` | digital | No | Debounced pin level (`0` or `1`) for IR sensor 1 and 2 |
| `ir1_events`, `ir2_events` | `int` | count | No | Cumulative obstacle entry transitions on IR1 and IR2 |
| `vehicle_count` | `int` | count | No | Cumulative state-machine validated vehicle crossings |
| `last_direction` | `string` | — | No | `"none"`, `"1_to_2"`, `"2_to_1"`, or `"simultaneous"` |
| `last_crossing_ms` | `int` | `ms` | No | Transit time between first and second IR gate on last crossing |
| `last_speed_mps` | `float` | $\text{m/s}$ | **Yes (`null`)** | Estimated speed (`null` when `IR_SENSOR_SPACING_M == 0.0`) |

---

## 3. InfluxDB 2.x Measurement Schema

- **Bucket:** `structural_health` (Organization: `pes-iot`)
- **Measurement:** `bridge_telemetry`
- **Tags:**
  - `device_id` (e.g., `esp32-bridge-01`)
  - `firmware_version` (e.g., `2.0.0`)
  - `imu_chip` (`0x68_MPU6050`, `0x70_MPU6500`, or hex value)
  - `calibrated` (`true` or `false`)
  - `data_source` (`sensor` or `synthetic`)
  - `last_direction` (`none`, `1_to_2`, `2_to_1`, `simultaneous`)
- **Fields:** All numeric and boolean telemetry keys from Section 2 (`vibration_rms_g`, `vibration_peak_g`, `ax_g`, `ay_g`, `az_g`, `gx_dps`, `gy_dps`, `gz_dps`, `hx711_raw_counts`, `hx711_net_counts`, `hx711_filtered_counts`, `calibration_factor`, optional `load_grams`, `ir1_state`, `ir2_state`, `ir1_events`, `ir2_events`, `vehicle_count`, `last_crossing_ms`, optional `last_speed_mps`, `last_direction_str`).

---

## 4. Experimental & Sample CSV Schema (`data/experimental/` & `data/sample/`)

Every CSV recorded by `scripts/record_trial.py` or exported by `scripts/export_data.py` contains 33 columns:

`timestamp,run_id,condition,data_source,device_id,seq,uptime_ms,imu_who_am_i,vibration_rms_g,vibration_peak_g,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx711_raw_counts,hx711_net_counts,hx711_filtered_counts,hx711_calibrated,calibration_factor,load_grams,ir1_state,ir2_state,ir1_events,ir2_events,vehicle_count,last_direction,last_crossing_ms,last_speed_mps,applied_mass_g,load_position,notes`
