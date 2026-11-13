"""Synthetic MQTT Pipeline Verification Script — Structural Health IoT Analytics.

Publishes clearly labelled synthetic test telemetry packets (`"data_source": "synthetic"`)
to the local Mosquitto broker and optionally verifies that the Python ingestion service
writes them into InfluxDB 2.x.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import List, Optional

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def build_synthetic_test_payloads(device_id: str = "esp32-bridge-01", count: int = 3) -> List[dict]:
    """Create clearly labelled synthetic test payloads covering baseline, load, and crossing."""
    payloads = []
    for i in range(1, count + 1):
        is_crossing = (i == count)
        payloads.append(
            {
                "device_id": device_id,
                "firmware_version": "2.0.0-synthetic-test",
                "data_source": "synthetic",
                "seq": i,
                "uptime_ms": i * 1000,
                "imu_ready": True,
                "imu_who_am_i": 112,
                "vibration_rms_g": 0.068 if is_crossing else 0.012,
                "vibration_peak_g": 0.195 if is_crossing else 0.031,
                "ax_g": 0.014 if is_crossing else 0.004,
                "ay_g": -0.011 if is_crossing else -0.003,
                "az_g": 0.994,
                "gx_dps": 1.45 if is_crossing else 0.12,
                "gy_dps": -1.10 if is_crossing else -0.08,
                "gz_dps": 0.55 if is_crossing else 0.05,
                "hx711_ready": True,
                "hx711_calibrated": False,
                "calibration_factor": 0.0,
                "hx711_raw_counts": -381709 + (4200 if is_crossing else -25),
                "hx711_net_counts": 4200 if is_crossing else -25,
                "hx711_filtered_counts": 3950.5 if is_crossing else -18.2,
                "load_grams": None,
                "ir1_state": 0 if is_crossing else 1,
                "ir2_state": 0 if is_crossing else 1,
                "ir1_events": 1 if is_crossing else 0,
                "ir2_events": 1 if is_crossing else 0,
                "vehicle_count": 1 if is_crossing else 0,
                "last_direction": "1_to_2" if is_crossing else "none",
                "last_crossing_ms": 480 if is_crossing else 0,
                "last_speed_mps": None,
            }
        )
    return payloads


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Publish synthetic MQTT test messages and verify InfluxDB storage.")
    parser.add_argument("--host", default=os.getenv("MQTT_BROKER_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_BROKER_PORT", "1883")))
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME", "bridge_iot"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD", "bridge_iot_pass"))
    parser.add_argument("--device-id", default="esp32-bridge-01")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--verify-influx", action="store_true", help="Verify written points in InfluxDB after publishing")
    args = parser.parse_args(argv)

    topic = f"structural-health/{args.device_id}/telemetry"
    payloads = build_synthetic_test_payloads(device_id=args.device_id, count=args.count)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if args.username:
        client.username_pw_set(args.username, args.password)

    print(f"[TEST] Connecting to MQTT broker {args.host}:{args.port}...")
    client.connect(args.host, args.port, keepalive=15)
    client.loop_start()

    for idx, payload in enumerate(payloads, start=1):
        encoded = json.dumps(payload)
        info = client.publish(topic, encoded, qos=0)
        info.wait_for_publish(timeout=5.0)
        print(f"  [PUBLISHED #{idx}] topic={topic} | seq={payload['seq']} | data_source=synthetic")
        time.sleep(0.4)

    client.loop_stop()
    client.disconnect()

    if args.verify_influx:
        time.sleep(1.5)
        influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        influx_token = os.getenv("INFLUXDB_TOKEN", "structural-health-iot-local-dev-token-2026")
        influx_org = os.getenv("INFLUXDB_ORG", "pes-iot")
        influx_bucket = os.getenv("INFLUXDB_BUCKET", "structural_health")

        ic = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
        flux = f"""
from(bucket: "{influx_bucket}")
  |> range(start: -15m)
  |> filter(fn: (r) => r["_measurement"] == "bridge_telemetry" and r["device_id"] == "{args.device_id}" and r["data_source"] == "synthetic")
  |> count()
"""
        tables = ic.query_api().query(flux, org=influx_org)
        ic.close()
        total_points = sum(rec.get_value() for tbl in tables for rec in tbl.records)
        print(f"[VERIFY] InfluxDB query returned {total_points} field records for synthetic test on '{args.device_id}'.")
        if total_points == 0:
            print("[ERROR] No synthetic test points found in InfluxDB!")
            return 1
        print("[SUCCESS] End-to-end Mosquitto -> Python Ingestor -> InfluxDB verification passed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
