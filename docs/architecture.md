# System Architecture

## Objective

Monitor a tabletop bridge-like structure under static loads and toy-vehicle crossings. Relate measured support reaction and displacement to vibration behaviour and traffic events.

## Functional pipeline

**Perception → Network → Application**

- **Perception:** MPU6050, VL53L0X, bar load cell + HX711, IR break-beam.
- **Network:** ESP32 Wi-Fi connection; MQTT publish/subscribe.
- **Application:** ThingSpeak channel, historical plots, Python analytics and a simple ML classifier.

This also maps to the course's five required stages:

| Stage | Implementation |
|---|---|
| Sense | Four agreed sensing channels |
| Ingest | ESP32 publishes timestamped MQTT data |
| Process | ESP32/backend computes sensor summaries and derived features |
| Store | ThingSpeak retains channel updates |
| Analyze | Compare experimental conditions; visualize and evaluate a small classifier |

## Four ThingSpeak fields

| Field | Name | Unit / interpretation |
|---|---|---|
| 1 | vibration_rms | g; RMS of dynamic acceleration after baseline/gravity treatment |
| 2 | deflection_mm | mm; change from unloaded ToF baseline |
| 3 | support_reaction_g | g-equivalent from calibrated support reaction |
| 4 | vehicle_count | cumulative detected crossings |

The MQTT payload should update all four fields together. Use a 15-second or longer cloud update interval for the free ThingSpeak service; local sensor sampling can be faster.

## Processing notes

- MPU6050: sample locally at a suitable rate (initial target ~100 Hz); derive RMS and peak features per reporting window.
- ToF: record unloaded baseline distance; deflection is the signed difference from this baseline.
- Load cell: tare and calibrate with known loads; describe the result as one support's reaction.
- IR gate: count one interruption per crossing, with debounce/re-arm logic to prevent duplicate counts.

## Experiments

1. **Static loading:** apply known loads at a marked position; record support reaction and displacement. Optionally capture vibration at rest.
2. **Vehicle crossing:** pass the same toy vehicle across the bridge repeatedly at a reasonably consistent speed; correlate crossings with vibration and other response measurements.

Record mass, placement, number of trials, approximate speed/handling method, calibration factor, sensor sampling settings and timestamps.

## ML scope

Use a simple, interpretable model (Decision Tree preferred for speed/explainability; Random Forest only if the dataset supports it). Predict experimental response/operation class labels defined from controlled trials. Do not label outputs as structural failure or safety predictions.

Use train/test separation by trial or run, not random splitting of highly adjacent samples from the same run. Report confusion matrix and accuracy; avoid claims from a tiny dataset.

## Network and security notes

- Keep Wi-Fi passwords, ThingSpeak write/read keys, MQTT usernames and passwords out of source control.
- Use local configuration/secrets not committed to Git.
- Prefer TLS where feasible; if an unencrypted test connection is used on a trusted lab network, document the limitation and do not publish credentials or expose the broker.
