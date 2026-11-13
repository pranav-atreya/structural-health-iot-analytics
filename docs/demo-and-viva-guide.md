# Live Demonstration & Viva-Voce Guide (`docs/demo-and-viva-guide.md`)

**Course:** Internet of Things (UE24CS342AA3) — PES University  
**Team:**
- Pranav Shashikiran Atreya (PES2UG24CS912)
- Yash Raghavendra A (PES2UG24CS913)
- Hemaksh Breja (PES2UG24CS191)
- Kashyap V P (PES2UG24CS218)

---

## Part 1: 10-Step Live Demonstration Sequence

Follow this exact sequence during the project evaluation to demonstrate every stage of **Sense → Ingest → Process → Store → Analyze**:

### Step 1 — ESP32 Boot & Hardware Self-Test
1. Plug the ESP32 DevKit V1 into USB and open Arduino IDE **Serial Monitor** at `115200` baud.
2. Press the `EN` (Reset) button on the ESP32.
3. Point out the boot diagnostic banner showing:
   - `[1] INITIALISING IMU` → `MPU address: 0x68`, `WHO_AM_I: 0x68` (or `0x70` MPU-6500), `IMU: ONLINE`
   - `[2] INITIALISING HX711 LOAD CELL` → `HX711: ONLINE`, automatic unloaded tare (`New zero offset: ...`)
   - `[3] IR MODULES` → initial GPIO states on `GPIO 26` and `GPIO 27`

### Step 2 — Live 10 Hz Serial Sensor Stream & Interactive Commands
1. Show the 10 Hz CSV stream (`time_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx_raw,hx_net,hx_filtered,ir1,ir2`).
2. Lightly press on the bridge deck over the instrumented support to show `hx_net` and `hx_filtered` responding in real time.
3. Send `T` in Serial Monitor to demonstrate live re-taring, and `S` to print the full diagnostic summary.

### Step 3 — Start Local Docker Stack & Show MQTT Publishing
1. In PowerShell, start the backend stack:
   ```powershell
   .\scripts\start_stack.ps1
   ```
2. Send `M` in Serial Monitor (or check `[MQTT] Connected to broker ...`) to show the 1 Hz JSON telemetry packet being published to `structural-health/esp32-bridge-01/telemetry`.

### Step 4 — Python MQTT Ingestor Validation Logs
1. In PowerShell, run:
   ```powershell
   docker compose logs --tail 25 -f mqtt_ingestor
   ```
2. Point out log lines showing `Wrote point #... | device=esp32-bridge-01 seq=... rms_g=... hx_filt=... veh=...`.

### Step 5 — InfluxDB 2.x Time-Series Storage
1. Open `http://localhost:8086` (login from `.env`) or run `python scripts/export_data.py --last 5m` to show points stored inside the `structural_health` bucket under measurement `bridge_telemetry`.

### Step 6 — Live Grafana Dashboard (`http://localhost:3000`)
1. Open `http://localhost:3000` → **Structural Health IoT Analytics — Bridge Prototype Monitor**.
2. Demonstrate:
   - Tapping the bridge deck → **Panel 1 (Vibration RMS)** and **Panel 2 (Peak Vibration)** spike immediately.
   - Placing a weight on the bridge → **Panel 5a/5b (HX711 Net & Filtered Counts)** steps up.
   - Rolling the toy car across IR1 → IR2 → **Panel 7 (IR States/Events)**, **Panel 8 (Vehicle Crossing Count)**, and **Panel 9 (Direction `1_to_2` & Transit Time ms)** update live.

### Step 7 — Record an Actual Experimental Run to CSV
1. Run a live 20-second trial capture from PowerShell:
   ```powershell
   python scripts/record_trial.py --run-id DEMO_CAR_01 --condition vehicle_crossing --load-position "1_to_2" --duration 20 --notes "Live evaluation demo pass"
   ```
2. Roll the toy car across the bridge during the 20-second window and show the resulting CSV file saved under `data/experimental/`.

### Step 8 — Export & Inspect Dataset
1. Inspect the recorded trial or synthetic benchmark dataset:
   ```powershell
   python scripts/export_data.py --inspect data/sample/synthetic_trials.csv
   ```

### Step 9 — Generate Comparative Analytics Plots
1. Run the analytics script:
   ```powershell
   python analytics-ml/analyze_trials.py --data data/sample/synthetic_trials.csv
   ```
2. Open `analytics-ml/results/condition_comparison.png` and `analytics-ml/results/trial_timeseries.png` to show how `baseline`, `static_load`, and `vehicle_crossing` separate across vibration RMS and HX711 support reaction counts.

### Step 10 — Train & Evaluate the Decision Tree Classifier and Run Prediction
1. Run group-aware training and evaluation:
   ```powershell
   python analytics-ml/train_model.py --data data/sample/synthetic_trials.csv
   ```
2. Show the printed Decision Tree rules, Confusion Matrix (`analytics-ml/results/confusion_matrix.png`), and Feature Importance (`analytics-ml/results/feature_importance.png`).
3. Run a live single-sample prediction:
   ```powershell
   python analytics-ml/predict.py --vibration-rms-g 0.075 --vibration-peak-g 0.210 --hx711-filtered-counts 4200 --ir1-state 0 --vehicle-crossing-delta 1
   ```

---

## Part 2: Expected Viva Questions & Technical Answers

### Q1. Why did you choose an IMU (GY-521) for vibration monitoring?
**Answer:** The GY-521 provides a 3-axis MEMS accelerometer and 3-axis gyroscope over I²C (`GPIO 21`/`22`). By sampling acceleration at ~100 Hz (configured via `SMPLRT_DIV = 9` and DLPF `0x03` at ~44 Hz bandwidth) and removing the quasi-static $1\,g$ gravity vector using an exponential low-pass filter, we can measure both the **RMS vibration energy (`vibration_rms_g`)** and **transient peak excitation (`vibration_peak_g`)** induced when a vehicle crosses the aluminium bridge deck.

### Q2. Why did your firmware use direct I²C register access instead of `Adafruit_MPU6050`?
**Answer:** During integrated hardware diagnostics, our GY-521 module returned `WHO_AM_I` (`0x75`) values of both `0x68` (MPU-6050) and `0x70` (MPU-6500). High-level libraries like `Adafruit_MPU6050` hardcode a check for `WHO_AM_I == 0x68` and fail initialization when `0x70` is returned. Because registers `0x6B`, `0x19`–`0x1C`, and `0x3B`–`0x48` are identical across both chips, our low-level `Wire.h` driver accepts both `0x68` and `0x70` while honestly reporting the actual `imu_who_am_i` integer in every telemetry packet.

### Q3. Why is an HX711 module required with the Sharvi 1 kg load cell?
**Answer:** A four-wire bar load cell is a passive Wheatstone bridge of strain gauges whose differential output under load is only a few millivolts ($\sim 1\text{ mV/V}$). The ESP32's internal 12-bit SAR ADC lacks both the differential instrumentation amplifier gain and the bit resolution to read microvolt changes. The **HX711** provides a dedicated programmable-gain differential amplifier ($128\times$ gain on Channel A) and a 24-bit sigma-delta ADC read via a two-wire synchronous serial interface (`GPIO 32` DOUT, `GPIO 33` SCK).

### Q4. Why did you use TWO IR obstacle sensors instead of just one?
**Answer:** A single IR sensor can only detect that an obstacle was present in front of one point; it cannot distinguish a vehicle **fully crossing** the bridge from a car stopping and reversing at the entrance, nor can it determine **direction of travel** (`1_to_2` vs `2_to_1`) or **transit time (`last_crossing_ms`)** across the span. With two sensors (`GPIO 26` and `GPIO 27`) and a finite state machine (`CROSSING_IDLE` → `CROSSING_1_TO_2_PENDING` → `CROSSING_WAIT_CLEAR`), we prevent duplicate counting and capture direction and transit duration.

### Q5. Why did you choose MQTT over HTTP REST for ESP32 telemetry?
**Answer:** MQTT uses a persistent TCP connection with a tiny 2-byte fixed packet header and a publish/subscribe broker (`Mosquitto`), whereas HTTP requires repeated TCP handshakes and verbose text headers on every 1 Hz update. Furthermore, MQTT decouples the ESP32 publisher from multiple downstream consumers: both the **Python InfluxDB ingestor** and the **experimental trial recorder (`record_trial.py`)** subscribe to `structural-health/+/telemetry` simultaneously without increasing load on the ESP32.

### Q6. Why use InfluxDB 2.x instead of a relational SQL database (MySQL/PostgreSQL)?
**Answer:** Sensor telemetry is append-only, timestamp-indexed data arriving continuously at 1 Hz. A time-series database (TSDB) like **InfluxDB 2.x** is purpose-built for time-indexed writes, automatic retention policies (`30d`), indexed metadata tags (`device_id`, `calibrated`, `data_source`), and fast windowed aggregations (`last()`, `mean()`, `max()`, `pivot()`) in Flux.

### Q7. Why use Grafana for the frontend dashboard?
**Answer:** Grafana connects natively to InfluxDB 2.x, supports declarative YAML/JSON provisioning (`docker/grafana/`), refreshes panels live every 2 seconds, and provides calibrated gauges, multi-axis time-series plots, threshold alerts, and graceful `noValue` handling (e.g., displaying `"Uncalibrated (Raw Counts Active)"` when `load_grams` is `null`).

### Q8. Why did you choose a `DecisionTreeClassifier` instead of Deep Learning or a complex neural network?
**Answer:** Our feature space consists of 8 well-defined physical summary metrics (`vibration_rms_g`, `vibration_peak_g`, `hx711_filtered_counts`, `ir_event_rate`, etc.) across three experimental regimes (`baseline`, `static_load`, `vehicle_crossing`). A shallow Decision Tree is fast, requires minimal compute, does not overfit small tabular datasets when depth-limited, and outputs **explicit, human-readable threshold rules (`export_text`)** and Gini feature importances that can be directly verified against physical intuition.

### Q9. What does the load cell physically measure on your prototype?
**Answer:** Because the Sharvi 1 kg load cell supports **one end** of the aluminium bridge deck while the opposite end rests on a support block, the load cell physically measures the **vertical support reaction at the instrumented support**, *not* the total weight placed on the bridge. By static moment equilibrium ($\sum M = 0$), a load $W$ at mid-span transfers roughly $0.5\,W$ to the instrumented support, whereas the same load placed near the instrumented support transfers a larger fraction of $W$.

### Q10. Why is the load-cell output reported as uncalibrated counts until a known mass is used?
**Answer:** Strain-gauge sensitivity and mounting geometry vary with clamping torque and deck preload. Our preliminary test with an ~50 g bottle gave roughly 12,830 net counts (~256.6 counts/g), which is only an approximate observation because the bottle's exact mass was not verified on a precision balance. Reporting uncalibrated counts as grams would be scientifically dishonest; therefore our firmware and database always preserve `hx711_raw_counts`, `hx711_net_counts`, and `hx711_filtered_counts`, and set `load_grams = null` until a validated calibration factor (`counts/g`) is configured.

### Q11. Why is there no direct displacement (`deflection_mm`) measurement in the final system?
**Answer:** An optical Time-of-Flight sensor (`VL53L0X`) was considered during initial planning, but it was officially dropped from the prototype hardware (and millimetre/sub-millimetre deck sag is well below the $\pm 3\text{ mm}$ noise floor of a VL53L0X anyway). We updated all documentation, schemas, and ML features to reflect our three actual verified sensor channels rather than fabricating or estimating displacement.

### Q12. How is sensor noise handled in the firmware and pipeline?
**Answer:**
1. **IMU:** Hardware digital low-pass filter (`0x1A = 0x03`, ~44 Hz bandwidth) on the MPU chip + software exponential low-pass filter ($\alpha = 0.02$) to track and subtract gravity drift + RMS integration over 100 samples per 1-second window.
2. **HX711:** 10-sample averaging during unloaded tare (`scale.read_average(10)`) + continuous exponential moving average (`hxFiltered = 0.25 * hxNet + 0.75 * hxFiltered`) to suppress ADC flicker.
3. **IR Sensors:** 25 ms software debounce on both GPIO pins + a 150 ms all-clear holdoff (`CROSSING_WAIT_CLEAR`) before re-arming the vehicle crossing state machine.

### Q13. What happens if Wi-Fi or the MQTT broker disconnects during an experiment?
**Answer:** Sensor acquisition on the ESP32 is **100% non-blocking**. If Wi-Fi or Mosquitto is unreachable, the 100 Hz IMU loop, HX711 conversions, IR state machine, and 10 Hz USB Serial CSV output continue running without interruption or reboot loops, while `maintainNetworkNonBlocking()` attempts a quick reconnect only once every 5–10 seconds.

### Q14. Why is this system NOT a real-world structural failure prediction system?
**Answer:** Real structural health monitoring (SHM) for civil bridges requires calibrated modal analysis (natural frequencies, mode shapes, damping ratios), temperature compensation, multi-point strain gauges, and finite-element baseline models validated over years of environmental loading. Our prototype is an educational tabletop IoT system that demonstrates end-to-end sensor acquisition, MQTT ingestion, time-series storage, live visualization, and classification of controlled lab operating conditions (`baseline`, `static_load`, `vehicle_crossing`).
