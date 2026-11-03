# Equal Four-Way Project Responsibility Allocation

**Project:** IoT-Analytics for Structural Vibration, Deformation and Load Behaviour Monitoring

The complete project is allocated equally among the four team members. Each member is assigned **25% of the overall project scope**. The allocation spans all five IoT stages—Sense, Ingest, Process, Store and Analyze—plus validation and documentation. It is not a hardware-versus-software division.

## Project-wide allocation matrix

| IoT stage / activity | Pranav Shashikiran Atreya (PES2UG24CS912) | Yash Raghavendra A (PES2UG24CS913) | Hemaksh Breja (PES2UG24CS191) | Kashyap V P (PES2UG24CS218) |
|---|---|---|---|---|
| **Sense** | Define vibration measurement requirements; characterize MPU6050 readings and sampling | Define structural measurement setup; plan load and deflection measurements and sensor placement | Define vehicle-crossing event criteria and IR count validation procedure | Define measurement variables, trial labels and data-capture requirements |
| **Ingest** | Define ESP32 acquisition sequence, timestamping and sensor data packet | Define repeatable test-run procedure, event timing and experimental run identifiers | Configure MQTT publishing/receiving and cloud-ingestion workflow | Validate incoming data structure, timestamps and dataset consistency |
| **Process** | Process acceleration readings; calculate vibration RMS and peak | Calibrate load-cell readings and convert ToF baseline change to deflection | Decode MQTT payloads, map channel fields and check missing/invalid updates | Clean data, prepare features and organize experimental labels |
| **Store** | Define measurement units, field names and calibration metadata | Maintain experimental metadata including applied mass, placement and test condition | Configure ThingSpeak fields and cloud time-series storage | Organize exported datasets and maintain separation of sample and experimental data |
| **Analyze** | Analyze vibration trends and compare response across test conditions | Analyze load-versus-deflection and support-reaction behaviour | Analyze vehicle-count/time trends and relate crossings to structural measurements | Produce analytical visualizations and implement/evaluate the simple ML classifier |
| **Validate & document** | Validate vibration measurements and document acquisition methodology | Conduct repeatable physical trials and document mechanical setup and calibration | Verify end-to-end MQTT/cloud receipt and document communication workflow | Validate analytical outputs, report model evaluation and document findings/limitations |

## Equal allocation summary

| Team member | Allocated share |
|---|---:|
| Pranav Shashikiran Atreya | 25% |
| Yash Raghavendra A | 25% |
| Hemaksh Breja | 25% |
| Kashyap V P | 25% |
| **Total** | **100%** |

Each allocation spans the full project lifecycle. Team members should understand the common architecture and be prepared to explain their assigned activities during the review.

## Common project deliverables

All members coordinate on:
- The shared Sense → Ingest → Process → Store → Analyze pipeline.
- One agreed sensor-data schema and experiment protocol.
- Verification using actual prototype measurements.
- Final results, limitations and project documentation.

Synthetic/sample data may be used for development and testing, but must be clearly identified and must not be presented as physical experimental results.
