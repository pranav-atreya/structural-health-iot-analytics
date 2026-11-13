# Troubleshooting Guide (`docs/troubleshooting.md`)

## 1. ESP32 & Sensor Hardware Issues

### 1.1 IMU Prints `Unknown IMU identity!` or `IMU: FAILED`
- **Cause:** Loose SDA (`GPIO 21`) / SCL (`GPIO 22`) jumper wires, missing common `GND`, or `3V3` power not reaching the GY-521 board.
- **Note on `WHO_AM_I`:** Our firmware already accepts both `0x68` (MPU-6050) and `0x70` (MPU-6500). If it prints `WHO_AM_I: 0x70`, that is **normal and supported** (`MPU-6500 DETECTED!`).
- **Fix:** Check continuity between ESP32 `GPIO 21` → `SDA`, `GPIO 22` → `SCL`, `3V3` → `VCC`, and `GND` → `GND`. Press the `EN` (Reset) button on the ESP32.

### 1.2 `HX711: FAILED` or `HX711 NOT READY` on Boot
- **Cause:** `DT`/`DOUT` (`GPIO 32`) and `SCK` (`GPIO 33`) swapped, or HX711 `VCC` not powered.
- **Fix:** Confirm `DT` is on `GPIO 32` and `SCK` is on `GPIO 33`. Ensure the load cell is unloaded during boot or send `T` in Serial Monitor (`115200` baud) to re-tare.

### 1.3 `load_grams` is `null` in MQTT JSON / Grafana Shows `Uncalibrated (Raw Counts Active)`
- **Cause:** This is **intentional behaviour** when `HX711_CALIBRATION_FACTOR` is `0.0f`. We do not fabricate gram readings from uncalibrated ADC counts.
- **Fix:** Place a known reference mass (e.g., `100` g) over the instrumented support and send `C 100` in Serial Monitor (or update `HX711_CALIBRATION_FACTOR` in `secrets.h`).

### 1.4 IR Sensors Trigger Continuously or Do Not Count Vehicle Crossings
- **Cause:** The sensitivity trimpot on the digital IR obstacle module is set too high (reflecting off the bridge deck itself) or too low (missing the toy car).
- **Fix:** Adjust the onboard Phillips potentiometer on each IR module so the indicator LED turns ON only when the toy car passes in front of the emitter/detector pair, and turns OFF when the deck is clear.

---

## 2. Wi-Fi, MQTT & Windows Firewall Issues

### 2.1 ESP32 Connects to Wi-Fi, But Prints `[MQTT] Connect failed, rc=-2`
- **Cause 1 — Wrong IP Address:** `MQTT_BROKER_HOST` in `secrets.h` is still `"192.168.1.100"` or `"localhost"` instead of your laptop's current Wi-Fi IPv4 address.
  - **Fix:** Run `ipconfig` in PowerShell, find your **Wireless LAN adapter Wi-Fi → IPv4 Address**, update `MQTT_BROKER_HOST` in `secrets.h`, and re-upload.
- **Cause 2 — Windows Firewall Blocking Port 1883 on Public Wi-Fi Profile:**
  - **Fix:** Ensure your Wi-Fi network is set to **Private** in Windows Network Settings, or allow inbound TCP port `1883` in Windows Defender Firewall:
    ```powershell
    New-NetFirewallRule -DisplayName "Mosquitto MQTT 1883" -Direction Inbound -LocalPort 1883 -Protocol TCP -Action Allow
    ```

### 2.2 `[MQTT] Connect failed, rc=4` or `rc=5` (Bad Username/Password / Not Authorized)
- **Cause:** `MQTT_USERNAME` / `MQTT_PASSWORD` in `firmware/structural_health_monitor/secrets.h` do not match `.env`.
- **Fix:** Verify both files use `bridge_iot` and `bridge_iot_pass` (or your chosen matching credentials) and restart the stack (`.\scripts\start_stack.ps1`).

---

## 3. Docker & Database Issues

### 3.1 `docker : failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`
- **Cause:** Docker Desktop is not running on Windows.
- **Fix:** Launch **Docker Desktop** from the Start Menu, wait ~20 seconds until the whale icon in the system tray is steady, and re-run `.\scripts\start_stack.ps1`.

### 3.2 Grafana Shows `No data` in Panels
- **Cause:** Either no MQTT telemetry has been published in the last 15 minutes, or the Grafana time range selector (`top-right`) does not cover the experiment window.
- **Fix:** Run the synthetic test publisher to verify the pipeline immediately:
  ```powershell
  python scripts/publish_synthetic_test.py --verify-influx
  ```
  Refresh Grafana at `http://localhost:3000`.
