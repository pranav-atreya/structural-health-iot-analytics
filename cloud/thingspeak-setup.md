# Optional Cloud Deployment Notes (ThingSpeak / Managed MQTT)

## Primary Architecture vs Optional Cloud Extension

The **primary runnable software stack** for this project is the self-contained local Docker Compose pipeline:

**ESP32 → Mosquitto MQTT → Python Ingestor → InfluxDB 2.x → Grafana**

This local stack supports 1 Hz telemetry updates without rate-limit throttling, preserves all 20+ telemetry fields and metadata tags, and requires no paid cloud accounts.

---

## Optional ThingSpeak / Cloud Bridge

If you wish to mirror summary metrics to ThingSpeak (or AWS IoT Core / HiveMQ Cloud) as an optional cloud demonstration:

1. **Active Measurement Channels (3 Sensor Groups — No ToF/Deflection):**
   - `field1`: `vibration_rms_g` ($g$)
   - `field2`: `vibration_peak_g` ($g$)
   - `field3`: `hx711_filtered_counts` (or `load_grams` when calibrated)
   - `field4`: `vehicle_count` (cumulative crossings)

   *(Note: `deflection_mm` from the dropped VL53L0X ToF sensor is no longer used.)*

2. **Rate Limit Consideration:**
   - Free ThingSpeak channels enforce a minimum 15-second update interval, whereas our local Mosquitto + InfluxDB + Grafana pipeline ingests at 1 Hz (and Serial logs at 10 Hz).
   - Keep credentials (`secrets.h`, `.env`) excluded from Git at all times.
