# IoT Security Architecture & Threat Analysis (`docs/security.md`)

Aligned with **Unit 4 (IoT Security)** of PES University course **UE24CS342AA3**.

---

## 1. Implemented Prototype Security Controls

### 1.1 Secret & Credential Isolation
- **Firmware Secrets (`secrets.h`):** Wi-Fi SSID, Wi-Fi password, and MQTT credentials are isolated in `firmware/structural_health_monitor/secrets.h`, which is excluded via `.gitignore`. Only `secrets.example.h` (with placeholder values) is committed to Git.
- **Backend Environment (`.env`):** Mosquitto, InfluxDB, and Grafana credentials and tokens are read from `.env` (excluded via `.gitignore`), with `.env.example` committed as a template.

### 1.2 Authenticated MQTT Broker (`eclipse-mosquitto:2`)
- On container startup, `docker/mosquitto/entrypoint.sh` hashes `MQTT_USERNAME` and `MQTT_PASSWORD` using `mosquitto_passwd -b` into `/tmp/mosquitto.passwd` (`chmod 0700`) and sets `allow_anonymous false`.
- Unauthenticated MQTT clients are rejected at the broker level unless `MQTT_ALLOW_ANONYMOUS=true` is explicitly enabled for isolated debugging.

### 1.3 Network Exposure Minimisation (Principle of Least Privilege)
- **InfluxDB (`127.0.0.1:8086`)** and **Grafana (`127.0.0.1:3000`)** are bound strictly to the laptop's loopback interface (`127.0.0.1`) in `docker-compose.yml`. Other devices on the Wi-Fi LAN cannot directly access the database or dashboard ports.
- **Mosquitto (`0.0.0.0:1883`)** is the only port reachable over the local Wi-Fi LAN so the ESP32 can publish telemetry, and it requires username/password authentication.
- The Python ingestion service (`sh_mqtt_ingestor`) exposes **zero host ports** and communicates with Mosquitto and InfluxDB solely over the internal Docker bridge network.

### 1.4 Strict Telemetry Validation & Sanitization (`validator.py`)
- Incoming MQTT payloads are parsed with a custom JSON constant hook that immediately rejects `NaN`, `Infinity`, and `-Infinity`.
- All numeric fields are type-checked and range-checked (e.g., `vibration_rms_g >= 0`, `ir1_state in {0, 1}`).
- Deprecated or unexpected fields (such as `deflection_mm`) are stripped before database ingestion.
- Malformed packets are logged and discarded without crashing the ingestion service.

---

## 2. Limitations of a Local Lab Deployment

Because this system is designed to run on a local student laptop over a shared 2.4 GHz lab/hotspot Wi-Fi network without paid certificates:

1. **Plaintext MQTT over TCP (Port 1883, No TLS):**
   - Although Mosquitto requires a username and password, standard MQTT over port `1883` transmits credentials and JSON payloads in plaintext over the local Wi-Fi LAN. An attacker on the same Wi-Fi subnet could sniff packets or replay telemetry.
2. **Pre-Shared Static Credentials:**
   - The ESP32 uses a shared username/password in `secrets.h` rather than per-device X.509 client certificates or hardware secure elements (ATECC608A / ESP32 flash encryption).
3. **No Application-Layer Message Signing:**
   - Payloads do not carry an HMAC/cryptographic signature or RTC-synchronized anti-replay nonce (`uptime_ms` and `seq` are monotonic per boot).

---

## 3. Production / Cloud Hardening Roadmap (MQTTS + TLS 1.3)

To upgrade this prototype for an untrusted or cloud network deployment:

1. **Enable TLS (`mqtts://` on Port 8883):**
   - Provision a CA certificate and server certificate on Mosquitto (or use AWS IoT Core / HiveMQ Cloud).
   - Switch the ESP32 from `WiFiClient` to `WiFiClientSecure` and verify the broker's root CA certificate (`espWiFiClient.setCACert(root_ca_pem)`).
2. **Per-Device Credentials & ACLs:**
   - Configure a Mosquitto ACL file restricting `bridge_iot` to `topic write structural-health/esp32-bridge-01/telemetry` and `ingestor_service` to `topic read structural-health/+/telemetry`.
3. **ESP32 Flash Encryption & Secure Boot:**
   - Enable ESP-IDF Flash Encryption so `secrets.h` credentials cannot be extracted via physical UART/SPI flash readout.
