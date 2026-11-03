# IoT-Analytics for Structural Vibration, Deformation and Load Behaviour Monitoring

An ESP32-based IoT system that monitors the response of a tabletop bridge structure under static loading and vehicle crossings. The project collects vibration, displacement, support-reaction and vehicle-count measurements, transfers them over MQTT, stores them in ThingSpeak, and analyzes the resulting data. A small supervised ML model is an additional part of the analytics workflow, not a replacement for the IoT pipeline.

## Team

- Pranav Shashikiran Atreya — PES2UG24CS912
- Yash Raghavendra A — PES2UG24CS913
- Hemaksh Breja — PES2UG24CS191
- Kashyap V P — PES2UG24CS218

## Project workflow

**Sense → Ingest → Process → Store → Analyze**

1. Sense: MPU6050 (vibration), VL53L0X (beam displacement), load cell + HX711 (one support reaction), and an IR break-beam pair (vehicle crossings).
2. Ingest: ESP32 sends timestamped summaries via MQTT over Wi-Fi.
3. Process: compute vibration RMS/peak, displacement relative to an unloaded baseline, calibrated support reaction, and vehicle counts.
4. Store: ThingSpeak channel with four fields.
5. Analyze: compare static-loading and vehicle-crossing experiments; use a simple, interpretable classifier on measured features as an additional analytics element.

## Planned sensing channels

| Channel | Hardware | Primary measurement |
|---|---|---|
| Vibration | MPU6050 | Acceleration and vibration features |
| Deformation | VL53L0X | Change in distance to beam underside |
| Support reaction | Bar load cell + HX711 | Calibrated reaction at one support |
| Vehicle count | IR emitter + phototransistor receiver | Beam interruptions / crossing events |

**Measurement note:** the single load cell measures the reaction at its mounted support, not the total load on the bridge. The physical mounting and calibration must be documented. The ToF value is converted to deflection using the unloaded baseline.

## Planned software stack

- ESP32 firmware: Arduino IDE / C++
- Connectivity: Wi-Fi + MQTT
- Cloud ingestion and time-series storage: ThingSpeak
- Analytics and ML: Python, Pandas, NumPy, Matplotlib/Plotly, scikit-learn

## Repository layout

- `docs/` — architecture, experimental method, team allocation and review notes
- `hardware/` — circuit notes, pin map, BOM and mechanical assembly
- `firmware/` — ESP32 sensor acquisition and MQTT publishing
- `cloud/` — ThingSpeak and MQTT setup notes
- `analytics-ml/` — preprocessing, analytics, model training and evaluation
- `data/sample/` — clearly labelled synthetic/test data only
- `data/experimental/` — actual measurements collected from the prototype (do not commit secrets)

## Getting started

1. Read `docs/architecture.md` and `docs/team-responsibilities.md`.
2. Follow `hardware/bom.md` and `hardware/pin-map.md`.
3. Configure ThingSpeak using `cloud/thingspeak-setup.md`. Keep API keys and MQTT credentials out of Git.
4. Use `data/sample/` only for software development until physical measurements are available.
5. Record experimental conditions and calibration details alongside every real dataset.

## Scope discipline

The prototype is a tabletop educational experiment. It does **not** certify bridge safety, detect real-world structural failure, or provide a validated structural-health diagnosis. The ML model will classify the experimental conditions represented in the collected training data. Report held-out evaluation results honestly.

## Course alignment

- Unit 1: ESP32, sensors, embedded C/C++, GPIO, I²C and interrupt handling.
- Unit 2: Wi-Fi connectivity and MQTT publish/subscribe.
- Unit 3: IoT data pipeline, cloud integration, analytics and introductory ML.
- Unit 4: credential handling, network exposure and basic IoT security considerations.
