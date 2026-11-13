# Experimental Protocol — Tabletop Bridge Structural Health Trials

> **Data Integrity Policy:** All tables below are blank templates for recording real physical measurements from the tabletop bridge prototype. Never fill these tables with fabricated values or confuse `data/sample/synthetic_trials.csv` with physical trial results.

---

## 1. Pre-Trial Setup, Tare & Load-Cell Calibration

### 1.1 Mechanical & Electrical Checklist
1. Place the wooden base on a flat, rigid lab bench.
2. Position the cast-iron support blocks and verify the Sharvi 1 kg bar load cell is securely supporting the instrumented end of the aluminium scale deck.
3. Verify the GY-521 IMU is fixed firmly to the bridge deck near mid-span and its jumper wires do not pull or damp the deck.
4. Align IR Sensor 1 (`GPIO 26`) and IR Sensor 2 (`GPIO 27`) at the two ends of the bridge span so the toy car interrupts each beam cleanly without scraping the sensor modules.
5. Measure the centre-to-centre spacing between IR1 and IR2 in metres using a ruler and record it below (enter into `IR_SENSOR_SPACING_M` in `secrets.h` if speed estimation is desired).

### 1.2 Tare Procedure
1. Remove all external weights and the toy car from the bridge deck.
2. On ESP32 boot (or by sending `T` in Serial Monitor at `115200` baud), allow the HX711 to average 10 unloaded readings to set `hxZero`.
3. Confirm `hx_net` and `hx_filtered` fluctuate near `0` counts at rest.

### 1.3 Two-Point / Known-Mass Calibration Procedure
A preliminary test with an unverified ~50 g bottle produced roughly 12,830 net counts (~256.6 counts/g). To perform a valid calibration before reporting grams:
1. Tare the unloaded bridge (`T` command).
2. Place a verified reference mass $M_{\text{ref}}$ (e.g., $50\text{ g}$, $100\text{ g}$, or $200\text{ g}$ weighed on a digital scale) directly over the instrumented support.
3. Send `C <grams>` in Serial Monitor (e.g., `C 100.0`) or run:
   ```powershell
   python scripts/calibrate_load_cell.py --known-mass-g 100.0 --net-counts <observed_hx_net>
   ```
4. Record the calibration metadata in the blank log below:

| Parameter | Measured Value (Fill During Lab Session) |
|---|---|
| Date & Time of Calibration | |
| Reference Mass Used ($M_{\text{ref}}$, g) | |
| Unloaded Tare Offset (`hxZero`, counts) | |
| Loaded Raw Counts (`hx_raw`, counts) | |
| Loaded Net Counts (`hx_net`, counts) | |
| Computed `HX711_CALIBRATION_FACTOR` ($\text{counts}/g$) | |
| IR Sensor 1 to IR Sensor 2 Spacing ($\text{m}$) | |

---

## 2. Reproducible Experiment Series

Perform at least **4 independent runs per condition** (`baseline`, `static_load`, `vehicle_crossing`) so that group-aware train/test splitting by `run_id` has sufficient independent runs.

### Experiment A — No-Load Baseline (`condition = baseline`)
- **Procedure:** Leave the bridge completely unloaded and undisturbed on the bench for 30 seconds per run.
- **Command:**
  ```powershell
  python scripts/record_trial.py --run-id EXP_BASE_01 --condition baseline --duration 30 --notes "Unloaded baseline run 1"
  ```

### Experiment B — Static Loading with Known Masses (`condition = static_load`)
- **Procedure:** Tare the bridge unloaded, then place a known mass ($50\text{ g}$, $100\text{ g}$, $150\text{ g}$, $200\text{ g}$) at a marked deck position (`mid-span` or `near-support`). Record for 30 seconds per run. Remove the mass and check zero return between runs.
- **Command:**
  ```powershell
  python scripts/record_trial.py --run-id EXP_LOAD_01 --condition static_load --applied-mass-g 100 --load-position "mid-span" --duration 30 --notes "100g static load at mid-span"
  ```

### Experiment C — Load Placement Position Comparison (`condition = static_load`)
- **Procedure:** Using the same known mass (e.g., $100\text{ g}$), record separate runs at:
  1. `near-instrumented-support` (1/4 span from load cell)
  2. `mid-span` (1/2 span)
  3. `far-support` (3/4 span away from load cell)
- **Expected Physical Principle:** Because the load cell measures the reaction at a single support ($R \approx W \cdot x / L$), `hx711_filtered_counts` (and calibrated `load_grams`) should decrease linearly as the same mass is moved away from the instrumented support toward the opposite support.

### Experiment D — Repeated Toy-Car Crossings (`condition = vehicle_crossing`)
- **Procedure:** Start a 45-second recording trial and roll the small toy car across the bridge deck from IR1 to IR2 (`1_to_2`) and from IR2 to IR1 (`2_to_1`), pausing 4–5 seconds between passes so the crossing state machine re-arms cleanly.
- **Command:**
  ```powershell
  python scripts/record_trial.py --run-id EXP_CAR_01 --condition vehicle_crossing --load-position "1_to_2" --duration 45 --notes "Toy car crossings 1->2"
  ```

---

## 3. Blank Experimental Trial Log Sheet

| Run ID | Condition | Applied Mass (g) | Load Position / Direction | Duration (s) | Mean `vibration_rms_g` | Max `vibration_peak_g` | Mean `hx711_filtered_counts` | Calibrated `load_grams` | Observed `vehicle_count` | Notes / Anomalies |
|---|---|---:|---|---:|---|---|---|---|---|---|
| `EXP_BASE_01` | `baseline` | 0 | `unloaded` | 30 | | | | | | |
| `EXP_BASE_02` | `baseline` | 0 | `unloaded` | 30 | | | | | | |
| `EXP_BASE_03` | `baseline` | 0 | `unloaded` | 30 | | | | | | |
| `EXP_BASE_04` | `baseline` | 0 | `unloaded` | 30 | | | | | | |
| `EXP_LOAD_01` | `static_load` | | `mid-span` | 30 | | | | | | |
| `EXP_LOAD_02` | `static_load` | | `mid-span` | 30 | | | | | | |
| `EXP_LOAD_03` | `static_load` | | `near-support` | 30 | | | | | | |
| `EXP_LOAD_04` | `static_load` | | `far-support` | 30 | | | | | | |
| `EXP_CAR_01` | `vehicle_crossing` | 0 | `1_to_2` | 45 | | | | | | |
| `EXP_CAR_02` | `vehicle_crossing` | 0 | `2_to_1` | 45 | | | | | | |
| `EXP_CAR_03` | `vehicle_crossing` | 0 | `1_to_2` | 45 | | | | | | |
| `EXP_CAR_04` | `vehicle_crossing` | 0 | `2_to_1` | 45 | | | | | | |
