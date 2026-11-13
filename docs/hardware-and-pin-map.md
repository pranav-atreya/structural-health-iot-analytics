# Hardware Specification & Pin Map (`docs/hardware-and-pin-map.md`)

## 1. Physical Prototype Components

- **Microcontroller:** ESP32 DevKit V1
- **Vibration Sensor (IMU):** GY-521 breakout board (labelled MPU6050; returns `WHO_AM_I` = `0x68` or `0x70`)
- **Support-Reaction Sensor:** Sharvi 1 kg four-wire aluminium bar load cell + HX711 24-bit amplifier module
- **Vehicle Crossing Sensors:** Two digital IR obstacle sensor modules (LM393 comparator based)
- **Bridge Structure:** Aluminium scale/ruler deck mounted on cast-iron support blocks over a wooden base
- **Test Excitation:** Known static masses and a small toy car

> **Dropped Sensor Notice:** The VL53L0X Time-of-Flight (ToF) sensor has been officially removed from the project. No direct displacement (`deflection_mm`) measurement is claimed or estimated.

---

## 2. ESP32 DevKit V1 Pin Map

| Peripheral | Module Terminal | ESP32 Pin | Direction | Notes |
|---|---|---|---|---|
| **GY-521 IMU** | `VCC` | `3V3` | Power | 3.3 V supply |
| **GY-521 IMU** | `GND` | `GND` | Power | Common ground |
| **GY-521 IMU** | `SDA` | `GPIO 21` | Bidirectional | I²C Data (100 kHz clock) |
| **GY-521 IMU** | `SCL` | `GPIO 22` | Output | I²C Clock (100 kHz clock) |
| **HX711 Module** | `VCC` | `3V3` | Power | 3.3 V supply ensures 3.3 V GPIO logic |
| **HX711 Module** | `GND` | `GND` | Power | Common ground |
| **HX711 Module** | `DT` / `DOUT` | `GPIO 32` | Input | Serial data output from HX711 |
| **HX711 Module** | `SCK` | `GPIO 33` | Output | Serial clock input to HX711 |
| **IR Sensor 1** | `VCC` / `GND` | `3V3` / `GND` | Power | Gate 1 (Entry) |
| **IR Sensor 1** | `OUT` | `GPIO 26` | Input | Digital obstacle signal (active `LOW` default) |
| **IR Sensor 2** | `VCC` / `GND` | `3V3` / `GND` | Power | Gate 2 (Exit) |
| **IR Sensor 2** | `OUT` | `GPIO 27` | Input | Digital obstacle signal (active `LOW` default) |

---

## 3. Load Cell to HX711 Wiring

| Load Cell Wire | HX711 Pin | Signal Description |
|---|---|---|
| **Red** | `E+` | Bridge excitation positive |
| **Black** | `E-` | Bridge excitation negative |
| **Green** | `A+` | Channel A differential input positive |
| **White** | `A-` | Channel A differential input negative |
| *(None)* | `B+`, `B-` | Unused secondary channel |

---

## 4. Sensor Characteristics & Limitations

1. **IMU (`WHO_AM_I` = `0x68` or `0x70`):**
   - Many GY-521 breakout boards sold as `MPU6050` are populated with `MPU-6500` dies (`WHO_AM_I = 0x70` / decimal `112`) or genuine `MPU-6050` dies (`WHO_AM_I = 0x68` / decimal `104`).
   - Both share the identical register layout for `PWR_MGMT_1 (0x6B)`, `SMPLRT_DIV (0x19)`, `CONFIG (0x1A)`, `GYRO_CONFIG (0x1B)`, `ACCEL_CONFIG (0x1C)`, and burst measurement registers `0x3B..0x48`.
   - Our firmware accepts both IDs and logs the actual `imu_who_am_i` integer in every telemetry packet.

2. **Load Cell + HX711 Calibration & Physical Meaning:**
   - The load cell measures the **vertical reaction force at the single instrumented support**, not the total bridge load. By static equilibrium of a simply supported span, a load $W$ placed at distance $x$ from the uninstrumented support of span $L$ produces a support reaction $R \approx W \cdot (x / L)$ at the instrumented support.
   - Preliminary testing with an ~50 g bottle produced roughly 12,830 counts (~256.6 counts/g), which is only a rough preliminary observation. Until calibrated with a verified reference mass, `HX711_CALIBRATION_FACTOR` defaults to `0.0f`, raw/net/filtered counts are reported, and `load_grams` is `null`.

3. **IR Obstacle Sensors & Spacing:**
   - Both sensors are debounced (`25 ms`) and transition-counted so a stationary car blocking a sensor does not increment counts repeatedly.
   - Crossing speed (`last_speed_mps`) is computed only when the physical distance between IR1 and IR2 (`IR_SENSOR_SPACING_M`) is measured and set $> 0.0\text{ m}$.
