# Hardware Pin Map & Wiring Reference (Verified on Prototype)

> **Scope Note:** The VL53L0X ToF sensor is not part of the prototype. Only the three verified sensor groups below are wired to the ESP32 DevKit V1.

## 1. Complete ESP32 Pin Assignment

| Sensor Group | Module Pin | ESP32 Pin | Signal Type / Configuration |
|---|---|---|---|
| **IMU (GY-521)** | `VCC` | `3V3` | 3.3 V power |
| **IMU (GY-521)** | `GND` | `GND` | Common ground |
| **IMU (GY-521)** | `SDA` | `GPIO 21` | I²C Data (100 kHz) |
| **IMU (GY-521)** | `SCL` | `GPIO 22` | I²C Clock (100 kHz) |
| **HX711 Load-Cell Amp** | `VCC` | `3V3` | 3.3 V power |
| **HX711 Load-Cell Amp** | `GND` | `GND` | Common ground |
| **HX711 Load-Cell Amp** | `DT` / `DOUT` | `GPIO 32` | Serial data output from HX711 |
| **HX711 Load-Cell Amp** | `SCK` | `GPIO 33` | Serial clock input to HX711 |
| **IR Obstacle Sensor 1** | `VCC` / `GND` | `3V3` / `GND` | 3.3 V power & common ground |
| **IR Obstacle Sensor 1** | `OUT` | `GPIO 26` | Digital input (Entry gate; active `LOW` default) |
| **IR Obstacle Sensor 2** | `VCC` / `GND` | `3V3` / `GND` | 3.3 V power & common ground |
| **IR Obstacle Sensor 2** | `OUT` | `GPIO 27` | Digital input (Exit gate; active `LOW` default) |

---

## 2. Sharvi 1 kg Four-Wire Bar Load Cell → HX711 Terminals

| Load Cell Wire Colour | HX711 Terminal | Function |
|---|---|---|
| **Red** | `E+` | Bridge excitation positive |
| **Black** | `E-` | Bridge excitation negative |
| **Green** | `A+` | Differential amplifier Channel A positive |
| **White** | `A-` | Differential amplifier Channel A negative |
| *(Unused)* | `B+`, `B-` | Channel B left unconnected |

---

## 3. IMU Register-Level Configuration Details

The physical GY-521 breakout board labelled `MPU6050` has returned `WHO_AM_I` (`0x75`) values of both `0x68` and `0x70` during integrated diagnostics. Our firmware uses direct I²C register access (`Wire.h`) and accepts both IDs:

- **I²C Address:** `0x68` (or `0x69` if `AD0` is pulled high)
- **WHO_AM_I (`0x75`):** Accepts `0x68` (MPU-6050) and `0x70` (MPU-6500); records actual integer value in `imu_who_am_i`
- **Power Management 1 (`0x6B`):** `0x00` (wakes chip from sleep)
- **Sample Rate Divider (`0x19`):** `9` ($1000\text{ Hz} / (1 + 9) = 100\text{ Hz}$)
- **DLPF Config (`0x1A`):** `0x03` (~44 Hz accelerometer / ~42 Hz gyroscope bandwidth)
- **Gyroscope Config (`0x1B`):** `0x08` ($\pm 500^\circ/\text{s}$ full scale, $65.5\text{ LSB}/(^\circ/\text{s})$)
- **Accelerometer Config (`0x1C`):** `0x08` ($\pm 4\,g$ full scale, $8192.0\text{ LSB}/g$)
- **Burst Read Base (`0x3B`):** 14 bytes (`ACCEL_XOUT_H` through `GYRO_ZOUT_L`)
