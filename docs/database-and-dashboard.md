# Database, MQTT Broker & Grafana Dashboard Guide (`docs/database-and-dashboard.md`)

## 1. Local Docker Compose Stack Architecture

The software pipeline runs locally via `docker-compose.yml` with four containers and persistent named volumes:

| Container Name | Image / Build | Host Port Binding | Internal Docker Hostname | Persistent Volume(s) |
|---|---|---|---|---|
| `sh_mosquitto` | `eclipse-mosquitto:2` | `0.0.0.0:1883` (LAN reachable by ESP32) | `mosquitto:1883` | `mosquitto_data`, `mosquitto_log` |
| `sh_influxdb` | `influxdb:2.7` | `127.0.0.1:8086` (Localhost only) | `influxdb:8086` | `influxdb_data`, `influxdb_config` |
| `sh_mqtt_ingestor` | `./backend/mqtt_ingestor` | *(None — internal worker)* | `mqtt_ingestor` | — |
| `sh_grafana` | `grafana/grafana:11.1.0` | `127.0.0.1:3000` (Localhost only) | `grafana:3000` | `grafana_data` |

> **Why Mosquitto binds `0.0.0.0:1883` while InfluxDB and Grafana bind `127.0.0.1`:**
> The physical ESP32 connects over the Wi-Fi LAN to the laptop's IPv4 address on port `1883`, whereas InfluxDB (`:8086`) and Grafana (`:3000`) only need to be accessed by the ingestion container (over the internal Docker bridge network) and the user's browser on `localhost`.

---

## 2. Starting and Stopping the Stack on Windows

```powershell
# 1. Initial one-time workspace setup (.env, secrets.h, Python deps)
.\scripts\setup.ps1

# 2. Start all four containers (builds ingestor image and provisions Grafana)
.\scripts\start_stack.ps1

# 3. Check container health and logs
docker compose ps
docker compose logs -f mqtt_ingestor

# 4. Stop containers while preserving all InfluxDB & Grafana data volumes
.\scripts\stop_stack.ps1
```

---

## 3. Finding Your Laptop's LAN IPv4 Address for the ESP32

The ESP32 cannot resolve `localhost` or the Docker service name `mosquitto`. It must connect to your Windows laptop's Wi-Fi IPv4 address:

```powershell
ipconfig
```

Look under **Wireless LAN adapter Wi-Fi → IPv4 Address** (for example `10.26.61.65` or `192.168.1.x`) and set:

```cpp
#define MQTT_BROKER_HOST "10.26.61.65"
```

inside `firmware/structural_health_monitor/secrets.h`. (`.\scripts\setup.ps1` detects and fills this automatically when creating `secrets.h`.)

---

## 4. Provisioned Grafana Dashboard (`http://localhost:3000`)

Log in at `http://localhost:3000` using `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` from `.env` (default in `.env.example`: `admin` / `bridge_grafana_admin`).

The dashboard **Structural Health IoT Analytics — Bridge Prototype Monitor** (`uid: structural-health-iot-main`) is automatically provisioned as the home dashboard and includes 10 panels across 4 rows:

1. **Panel 1 — Live Vibration RMS ($g$):** Gauge with green/yellow/red thresholds + time-series trend (`vibration_rms_g`).
2. **Panel 2 — Live Peak Vibration ($g$):** Gauge + time-series trend (`vibration_peak_g`).
3. **Panel 3 — Accelerometer Measurements ($g$):** 3-axis time series (`ax_g`, `ay_g`, `az_g`).
4. **Panel 4 — Gyroscope Measurements ($^\circ/\text{s}$):** 3-axis angular rate time series (`gx_dps`, `gy_dps`, `gz_dps`).
5. **Panel 5a/5b — HX711 Raw, Tare-Relative Net & Filtered Counts:** Time-series plot + live stat snapshot (`hx711_raw_counts`, `hx711_net_counts`, `hx711_filtered_counts`).
6. **Panel 6 — Calibrated Support Reaction ($g$):** Displays `load_grams` when calibrated, and cleanly displays `"Uncalibrated (Raw Counts Active)"` when `load_grams` is `null`.
7. **Panel 7 — IR Sensor 1 (`GPIO 26`) & Sensor 2 (`GPIO 27`) Activity:** Step plot of digital states (`ir1_state`, `ir2_state`) and cumulative transition counts (`ir1_events`, `ir2_events`).
8. **Panel 8 — Cumulative Vehicle Crossing Count:** Live counter (`vehicle_count`) from the two-sensor crossing state machine.
9. **Panel 9 — Crossing Direction, Transit Time & Speed:** Displays `last_direction` (`1_to_2` / `2_to_1`), `last_crossing_ms` ($\text{ms}$), and `last_speed_mps` ($\text{m/s}$, displaying `"Spacing Not Configured (0.0 m)"` when `IR_SENSOR_SPACING_M == 0.0`).
10. **Panel 10 — Sensor Connectivity & Hardware Identity Status:** Displays `seq`, `uptime_ms`, `imu_who_am_i` (mapped to `0x68 (MPU-6050)` or `0x70 (MPU-6500)`), and HX711 calibration state.
