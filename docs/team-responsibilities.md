# Team Responsibilities

This file contains **two distinct views** of the team's division of work. They serve different purposes and must not be merged.

## A. Actual internal execution split

This is the working arrangement used to complete the project efficiently. GitHub folders, implementation tasks and commits should follow these responsibilities.

### Pranav Shashikiran Atreya (PES2UG24CS912)
**Electronics, circuit design and embedded integration**
- Own overall circuit design and ESP32 pin allocation.
- Interface the four sensing channels with the ESP32.
- Develop and integrate sensor-acquisition firmware.
- Handle calibration and serial debugging.
- Configure the ESP32 network connection and integrate MQTT publishing with the cloud service.
- Coordinate end-to-end integration and system testing.

### Yash Raghavendra A (PES2UG24CS913)
**Mechanical design and physical prototype**
- Design and build the tabletop bridge/beam test structure.
- Fabricate the base, deck, supports and mounting arrangements.
- Mechanically mount the load cell and position the ToF/IR components.
- Ensure stability, alignment and repeatability of physical tests.
- Assist with calibration fixtures, controlled loading and vehicle-crossing experiments.

### Hemaksh Breja (PES2UG24CS191)
**IoT connectivity and cloud integration**
- Configure ThingSpeak channel and field definitions.
- Set up MQTT device credentials and publish/ingest path.
- Validate cloud reception using clearly labelled sample values before hardware is ready.
- Configure channel visualizations and data export/retrieval.
- Document network, protocol and cloud configuration.
- Integrate with actual ESP32 messages when available.

### Kashyap V P (PES2UG24CS218)
**Data analytics and machine learning**
- Set up Python environment and requirements.
- Develop data cleaning, preprocessing and derived-feature calculations.
- Build analytical plots and comparisons for loading and vehicle-crossing trials.
- Implement a small, interpretable supervised classifier for experimentally defined operating/response classes.
- Evaluate with a confusion matrix and held-out test data; document limitations.
- Replace synthetic development data with actual experimental data for final results.

## B. Separate equal four-way project-wide allocation

This is a separate project-wide allocation view, not the internal execution workflow above. It is intended to show that the overall project is divided into four broad, comparable work packages, with each member assigned one quarter of the full project scope.

Each package includes a balanced combination of project planning, technical design, implementation, validation and documentation across the complete project.

| Member | Equal project-wide work package | Scope |
|---|---|---|
| Pranav Shashikiran Atreya | Work Package 1 — System specification, sensing strategy and embedded-system design | Define system requirements and measurement plan; contribute to sensor selection, circuit/firmware design, data definitions, validation planning and technical documentation. |
| Yash Raghavendra A | Work Package 2 — Prototype engineering, instrumentation and experimental methodology | Develop structural prototype requirements; contribute to sensing/instrumentation layout, mounting and integration design, calibration methodology, experiment planning and results documentation. |
| Hemaksh Breja | Work Package 3 — IoT communication, cloud data pipeline and application interface | Contribute to end-to-end architecture, data model, MQTT/network design, cloud storage and visualization, integration testing and protocol/security documentation. |
| Kashyap V P | Work Package 4 — Data processing, analytics, ML and evaluation | Contribute to data requirements, feature design, preprocessing, analytical methods, simple ML workflow, evaluation strategy, result interpretation and documentation. |

**Equal-allocation interpretation:** the four work packages are intended as equal shares of the overall project scope, not as a hardware-versus-software division. They cover different technical domains but each includes specification, design decisions, implementation-related work, validation and documentation across the project lifecycle.

## Collaboration and handoffs

- The four members coordinate around one agreed data schema and experiment protocol.
- Sample/synthetic data must be labelled as such and must not be reported as experimental results.
- Actual completion, contributions and results should be updated as work progresses.
- Keep secrets and credentials out of commits.
