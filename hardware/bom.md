# Hardware Bill of Materials (BOM) — As-Built Prototype

## Active Sensing & Embedded Electronics

| Qty | Component | Role in Prototype | Status |
|---:|---|---|---|
| 1 | **ESP32 DevKit V1** | Microcontroller, I²C master, GPIO interrupt/polling, Wi-Fi + MQTT publisher | Integrated & tested |
| 1 | **GY-521 IMU Module (labelled MPU6050)** | 3-axis accelerometer + 3-axis gyroscope for deck vibration (~100 Hz; returns `WHO_AM_I` `0x68` or `0x70`) | Integrated & tested |
| 1 | **Sharvi 1 kg 4-Wire Bar Load Cell** | Strain-gauge full bridge mounted at one bridge support to measure support reaction | Integrated & tested |
| 1 | **HX711 Load-Cell Amplifier / 24-bit ADC** | Amplifies and digitizes the millivolt bridge output from the Sharvi 1 kg load cell | Integrated & tested |
| 2 | **Digital IR Obstacle Sensor Modules** | Active-LOW digital optical gates (`GPIO 26`, `GPIO 27`) for vehicle detection, counting, and direction | Integrated & tested |
| 1 | **Breadboard & Jumper Wires** | Common 3.3 V / GND distribution and signal routing | Integrated & tested |

> **Dropped Hardware Note:** The **VL53L0X Time-of-Flight (ToF)** distance sensor originally considered during early planning has been officially dropped from the prototype. There is no direct displacement (`deflection_mm`) sensor in the final hardware.

---

## Mechanical Bridge Prototype Materials

| Qty | Material | Description |
|---:|---|---|
| 1 | **Aluminium Scale / Ruler** | Used as the flexible tabletop bridge deck |
| 1 | **Wooden Base** | Rigid base supporting the bridge piers and load cell |
| 2 | **Cast-Iron Support Blocks** | Bridge abutments/supports |
| 1 | **Small Toy Car** | Test vehicle passed across the deck during dynamic crossing trials |
| — | **Reference Masses** | Known masses (e.g., 50 g, 100 g, 200 g) for load-cell calibration and static-load trials |

---

## Electrical & Mechanical Notes

- **Load-Cell Wiring to HX711:**
  - **Red** → `E+` (Excitation +)
  - **Black** → `E-` (Excitation −)
  - **Green** → `A+` (Signal +)
  - **White** → `A-` (Signal −)
  - `B+` and `B-` on the HX711 are unused.
- **3.3 V Logic Safety:** Power the GY-521 IMU, HX711, and both IR obstacle modules from the ESP32 `3V3` rail with a common `GND` so that no 5 V logic level is ever applied to an ESP32 GPIO pin.
- **Physical Interpretation of Load Cell:** Because the bar load cell supports one end of the aluminium deck, its output measures the **support reaction at the instrumented support**, not the total load placed on the bridge.
