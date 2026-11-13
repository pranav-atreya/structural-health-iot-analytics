# Team Responsibility Allocation (`docs/team-responsibilities.md`)

**Project:** Structural Health IoT Analytics  
**Course:** Internet of Things (UE24CS342AA3) — PES University

## Team Members

- **Pranav Shashikiran Atreya** — `PES2UG24CS912`
- **Yash Raghavendra A** — `PES2UG24CS913`
- **Hemaksh Breja** — `PES2UG24CS191`
- **Kashyap V P** — `PES2UG24CS218`

---

## 1. Practical Working Arrangement

To execute hardware integration and software development efficiently in parallel, the team coordinated around the following practical working arrangement:

- **Pranav Shashikiran Atreya (`PES2UG24CS912`) & Yash Raghavendra A (`PES2UG24CS913`):** Physical tabletop bridge assembly, mechanical mounting of the aluminium scale deck, Sharvi 1 kg load cell, GY-521 IMU, and dual IR obstacle modules, and physical sensor placement.
- **Pranav Shashikiran Atreya (`PES2UG24CS912`):** ESP32 firmware setup (`structural_health_monitor.ino`), register-level IMU driver (`0x68`/`0x70` compatibility), HX711 & IR state-machine integration, and hardware-to-software MQTT integration.
- **Hemaksh Breja (`PES2UG24CS191`) & Kashyap V P (`PES2UG24CS218`):** Backend Docker stack (`Mosquitto`, `InfluxDB 2.x`, `Grafana` dashboard provisioning), Python MQTT ingestion & validation service, trial recording/export CLI scripts, and Pandas/Scikit-learn analytics and Decision Tree ML pipeline.

---

## 2. Equal Four-Way Lifecycle Responsibility Matrix (25% Each)

Across the five required course IoT stages (**Sense → Ingest → Process → Store → Analyze**) plus validation and documentation, responsibilities are distributed equally (25% per member):

| IoT Stage / Activity | Pranav Shashikiran Atreya (`PES2UG24CS912`) | Yash Raghavendra A (`PES2UG24CS913`) | Hemaksh Breja (`PES2UG24CS191`) | Kashyap V P (`PES2UG24CS218`) |
|---|---|---|---|---|
| **Sense** | Register-level IMU (`0x68`/`0x70`) acquisition at ~100 Hz; ESP32 pin mapping & electrical integration | Mechanical bridge deck setup, Sharvi 1 kg load-cell support mounting, and IR gate alignment | IR obstacle sensor debounce criteria, directional crossing state-machine specification | Sensor measurement variables, trial condition definitions (`baseline`, `static_load`, `vehicle_crossing`) |
| **Ingest** | ESP32 non-blocking Serial CSV (10 Hz) & Wi-Fi/MQTT JSON (1 Hz) telemetry framing | Repeatable physical trial protocol, known-mass tare/calibration workflow, and run numbering | Eclipse Mosquitto broker setup, topic design (`structural-health/+/telemetry`), and Python MQTT subscriber | Telemetry JSON schema validation, non-finite value rejection, and timestamp alignment |
| **Process** | On-device gravity low-pass filtering, windowed `vibration_rms_g` and `vibration_peak_g`, and HX711 EMA filtering | Load-cell tare offset and known-mass calibration factor (`counts/g`) characterization at the instrumented support | Backend payload normalization, tag extraction (`device_id`, `imu_chip`, `calibrated`), and error handling | Dataset cleaning, per-run feature engineering (`accel_dynamic_g`, `gyro_magnitude_dps`, `ir_event_rate`) |
| **Store** | Define firmware telemetry keys, units, and calibration metadata flags (`hx711_calibrated`) | Maintain experimental trial metadata (`applied_mass_g`, `load_position`, `notes`) | Configure InfluxDB 2.x bucket (`structural_health`), measurement (`bridge_telemetry`), and Docker persistence | Manage CSV trial recording (`record_trial.py`), InfluxDB export (`export_data.py`), and `synthetic` vs `experimental` separation |
| **Analyze** | Correlate deck vibration RMS/peak with static loading and vehicle crossings | Analyze support-reaction counts vs load mass and load placement position | Provision the 10-panel Grafana live dashboard (`structural-health-dashboard.json`) and crossing analytics | Generate comparative Matplotlib plots (`analyze_trials.py`) and implement group-split `DecisionTreeClassifier` (`train_model.py`, `predict.py`) |
| **Validate & Document** | Verify ESP32 firmware compilation, Serial diagnostics, and hardware-software interface documentation | Document BOM, pin map, and reproducible experimental protocol templates | Verify Docker Compose stack health, Mosquitto auth, and database/dashboard documentation | Run automated `pytest` suite, validate ML statistical readiness checks, and maintain viva/analytics docs |

---

## 3. Equal Allocation Summary

| Team Member | SRN | Allocated Share |
|---|---|---:|
| Pranav Shashikiran Atreya | `PES2UG24CS912` | 25% |
| Yash Raghavendra A | `PES2UG24CS913` | 25% |
| Hemaksh Breja | `PES2UG24CS191` | 25% |
| Kashyap V P | `PES2UG24CS218` | 25% |
| **Total** | | **100%** |
