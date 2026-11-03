# Team Responsibilities

This document records **two separate views** of project responsibility. Keep them distinct.

# A. Internal execution split

This is the practical day-to-day arrangement used by the team to work in parallel and finish the prototype efficiently. GitHub implementation folders and handoffs follow this split.

## Pranav Shashikiran Atreya (PES2UG24CS912)
**Circuit design, electronics and embedded integration**
- Own the circuit design and ESP32 pin allocation.
- Interface all four sensing channels with the ESP32.
- Develop and integrate the sensor-acquisition firmware.
- Handle sensor calibration, serial debugging and embedded-side processing.
- Configure the ESP32 network connection and integrate MQTT publishing with the cloud service.
- Coordinate end-to-end integration and system testing.

## Yash Raghavendra A (PES2UG24CS913)
**Mechanical design and physical prototype**
- Design and build the tabletop bridge/beam test structure.
- Fabricate the base, deck, supports and mounting arrangements.
- Mechanically mount the load cell and position the ToF/IR components.
- Ensure stability, alignment and repeatability of physical tests.
- Assist with calibration fixtures, controlled loading and vehicle-crossing experiments.

## Hemaksh Breja (PES2UG24CS191)
**IoT connectivity and cloud integration**
- Configure the ThingSpeak channel and field definitions.
- Set up MQTT device credentials and the publishing/ingestion path.
- Validate cloud reception using clearly labelled sample values before hardware is ready.
- Configure channel visualizations and data export/retrieval.
- Document network, protocol and cloud configuration.
- Integrate with actual ESP32 messages when available.

## Kashyap V P (PES2UG24CS218)
**Data analytics and machine learning**
- Set up the Python environment and requirements.
- Develop data cleaning, preprocessing and derived-feature calculations.
- Build analytical plots and comparisons for loading and vehicle-crossing trials.
- Implement a small, interpretable supervised classifier for experimentally defined response conditions.
- Evaluate with a confusion matrix and held-out trials; document limitations.
- Replace synthetic development data with actual experimental data for final results.

# B. Separate equal four-way project-wide allocation

This is a distinct project-wide allocation view. It is **not** the internal pair-based execution workflow above. The overall project is divided into four equal work packages, each covering contributions across the full IoT lifecycle rather than dividing the project into hardware and software teams.

For planning purposes, the project is allocated as **100 contribution units: 25 units per member**. Each member has responsibilities in sensing, ingestion, processing, storage, analysis and validation/documentation.

| Project stage | Pranav — 25 units | Yash — 25 units | Hemaksh — 25 units | Kashyap — 25 units |
|---|---|---|---|---|
| **Sense** | Vibration measurement requirements, MPU6050 sampling and calibration plan | Structural test setup, sensor placement and load/deflection measurement method | Vehicle-count event definition and IR detection validation criteria | Measurement variables, experiment labels and dataset capture requirements |
| **Ingest** | ESP32 acquisition sequence, timestamps and common data-packet structure | Repeatable physical test/event procedure and run identification | MQTT publish/subscribe configuration and cloud ingestion | Incoming-data validation, timestamp checks and CSV/schema consistency |
| **Process** | Acceleration baseline treatment, vibration RMS and peak calculation | Load-cell calibration conversion and ToF baseline-to-deflection calculation | MQTT payload decoding, field mapping and missing/invalid update checks | Data cleaning, feature preparation and experiment-label preparation |
| **Store** | Define measurement units, field names and calibration metadata requirements | Maintain test-run metadata: applied mass, placement and experimental condition | ThingSpeak channel configuration and cloud time-series storage | Organize exported datasets and maintain sample-versus-experimental data separation |
| **Analyze** | Vibration response trends and comparison across experimental conditions | Load-versus-deflection and support-reaction analysis | Vehicle-count/time trends and comparison with measured structural response | Analytics visualizations and simple supervised ML classification/evaluation |
| **Validate & document** | Validate vibration readings and document embedded acquisition | Repeat static-load/vehicle-crossing trials and document the physical method | Validate end-to-end MQTT/cloud receipt and document protocol configuration | Validate analytical outputs/model evaluation and document findings and limitations |

**Equal-allocation summary**

- Pranav Shashikiran Atreya — 25%
- Yash Raghavendra A — 25%
- Hemaksh Breja — 25%
- Kashyap V P — 25%

The equal allocation is a project-wide responsibility matrix. It is separate from the practical pair-based execution split in Section A. Each member should be familiar with the overall pipeline and be able to explain their allocated project-wide tasks during review.

# Collaboration and handoffs

- All four members coordinate around one agreed data schema and experimental protocol.
- Sample/synthetic records are for software development only and must not be presented as physical experimental results.
- Keep implementation commits in the appropriate repository folders.
- Record actual tests, calibration factors and results as work is completed.
- Never commit Wi-Fi passwords, ThingSpeak API keys, MQTT usernames or passwords.
