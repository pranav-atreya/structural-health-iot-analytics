"""Experimental Trial Recording CLI — Structural Health IoT Analytics.

Records live timestamped sensor telemetry from the physical prototype (via MQTT
or USB Serial) into a structured CSV file under `data/experimental/`, without
ever overwriting previous experimental runs.

Supported condition labels:
  - baseline
  - static_load
  - vehicle_crossing

Usage examples:
  python scripts/record_trial.py --run-id EXP_01 --condition baseline --duration 30 --notes "Unloaded bridge deck"
  python scripts/record_trial.py --run-id EXP_02 --condition static_load --applied-mass-g 100 --load-position "mid-span" --duration 30
  python scripts/record_trial.py --run-id EXP_03 --condition vehicle_crossing --duration 45 --notes "Toy car passes 1->2"
  python scripts/record_trial.py --mode serial --serial-port COM3 --run-id EXP_04 --condition baseline --duration 20
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.mqtt_ingestor.validator import (  # noqa: E402
    TelemetryValidationError,
    parse_and_validate_payload,
)

load_dotenv(REPO_ROOT / ".env")

ALLOWED_CONDITIONS = ("baseline", "static_load", "vehicle_crossing")

CSV_COLUMNS = [
    "timestamp",
    "run_id",
    "condition",
    "data_source",
    "device_id",
    "seq",
    "uptime_ms",
    "imu_who_am_i",
    "vibration_rms_g",
    "vibration_peak_g",
    "ax_g",
    "ay_g",
    "az_g",
    "gx_dps",
    "gy_dps",
    "gz_dps",
    "hx711_raw_counts",
    "hx711_net_counts",
    "hx711_filtered_counts",
    "hx711_calibrated",
    "calibration_factor",
    "load_grams",
    "ir1_state",
    "ir2_state",
    "ir1_events",
    "ir2_events",
    "vehicle_count",
    "last_direction",
    "last_crossing_ms",
    "last_speed_mps",
    "applied_mass_g",
    "load_position",
    "notes",
]


def resolve_non_overwriting_csv_path(output_dir: Path, run_id: str, condition: str) -> Path:
    """Return a target CSV path, appending a UTC timestamp suffix if the file already exists."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in run_id)
    base_path = output_dir / f"{safe_run}_{condition}.csv"
    if not base_path.exists():
        return base_path

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    alt_path = output_dir / f"{safe_run}_{condition}_{stamp}.csv"
    counter = 1
    while alt_path.exists():
        alt_path = output_dir / f"{safe_run}_{condition}_{stamp}_{counter}.csv"
        counter += 1
    return alt_path


def build_csv_row_from_telemetry(
    raw_dict: Dict[str, Any],
    run_id: str,
    condition: str,
    data_source: str,
    applied_mass_g: float,
    load_position: str,
    notes: str,
    timestamp_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a validated telemetry dictionary and trial metadata into a CSV row dict."""
    if timestamp_iso is None:
        timestamp_iso = datetime.now(timezone.utc).isoformat()

    hx_cal = bool(raw_dict.get("hx711_calibrated", False))
    load_g = raw_dict.get("load_grams")
    if not hx_cal:
        load_g = ""
    elif load_g is None:
        load_g = ""

    speed_mps = raw_dict.get("last_speed_mps")
    if speed_mps is None:
        speed_mps = ""

    return {
        "timestamp": timestamp_iso,
        "run_id": run_id,
        "condition": condition,
        "data_source": data_source,
        "device_id": raw_dict.get("device_id", "esp32-bridge-01"),
        "seq": raw_dict.get("seq", 0),
        "uptime_ms": raw_dict.get("uptime_ms", 0),
        "imu_who_am_i": raw_dict.get("imu_who_am_i", 104),
        "vibration_rms_g": round(float(raw_dict.get("vibration_rms_g", 0.0)), 5),
        "vibration_peak_g": round(float(raw_dict.get("vibration_peak_g", 0.0)), 5),
        "ax_g": round(float(raw_dict.get("ax_g", 0.0)), 4),
        "ay_g": round(float(raw_dict.get("ay_g", 0.0)), 4),
        "az_g": round(float(raw_dict.get("az_g", 1.0)), 4),
        "gx_dps": round(float(raw_dict.get("gx_dps", 0.0)), 3),
        "gy_dps": round(float(raw_dict.get("gy_dps", 0.0)), 3),
        "gz_dps": round(float(raw_dict.get("gz_dps", 0.0)), 3),
        "hx711_raw_counts": int(raw_dict.get("hx711_raw_counts", 0)),
        "hx711_net_counts": int(raw_dict.get("hx711_net_counts", 0)),
        "hx711_filtered_counts": round(float(raw_dict.get("hx711_filtered_counts", 0.0)), 2),
        "hx711_calibrated": hx_cal,
        "calibration_factor": round(float(raw_dict.get("calibration_factor", 0.0)), 4),
        "load_grams": load_g,
        "ir1_state": int(raw_dict.get("ir1_state", 1)),
        "ir2_state": int(raw_dict.get("ir2_state", 1)),
        "ir1_events": int(raw_dict.get("ir1_events", 0)),
        "ir2_events": int(raw_dict.get("ir2_events", 0)),
        "vehicle_count": int(raw_dict.get("vehicle_count", 0)),
        "last_direction": str(raw_dict.get("last_direction", "none")),
        "last_crossing_ms": int(raw_dict.get("last_crossing_ms", 0)),
        "last_speed_mps": speed_mps,
        "applied_mass_g": round(float(applied_mass_g), 2),
        "load_position": load_position,
        "notes": notes,
    }


def write_rows_to_csv(csv_path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write a list of telemetry rows to disk using the canonical CSV schema."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_serial_csv_line(
    line: str,
    grav_state: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Parse a 10 Hz firmware CSV line into a normalized telemetry dictionary.

    Expected format:
      time_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,hx_raw,hx_net,hx_filtered,ir1,ir2
    """
    parts = [p.strip() for p in line.strip().split(",")]
    if len(parts) != 12:
        return None
    if parts[0] == "time_ms" or not parts[0].isdigit():
        return None

    try:
        uptime_ms = int(parts[0])
        ax_g = 0.0 if parts[1] == "NA" else float(parts[1])
        ay_g = 0.0 if parts[2] == "NA" else float(parts[2])
        az_g = 1.0 if parts[3] == "NA" else float(parts[3])
        gx_dps = 0.0 if parts[4] == "NA" else float(parts[4])
        gy_dps = 0.0 if parts[5] == "NA" else float(parts[5])
        gz_dps = 0.0 if parts[6] == "NA" else float(parts[6])
        hx_raw = 0 if parts[7] == "NA" else int(float(parts[7]))
        hx_net = 0 if parts[8] == "NA" else int(float(parts[8]))
        hx_filtered = 0.0 if parts[9] == "NA" else float(parts[9])
        ir1 = int(parts[10])
        ir2 = int(parts[11])
    except ValueError:
        return None

    alpha = 0.05
    if not grav_state.get("seeded", False):
        grav_state["bx"] = ax_g
        grav_state["by"] = ay_g
        grav_state["bz"] = az_g
        grav_state["seeded"] = True
    else:
        grav_state["bx"] = (1.0 - alpha) * grav_state["bx"] + alpha * ax_g
        grav_state["by"] = (1.0 - alpha) * grav_state["by"] + alpha * ay_g
        grav_state["bz"] = (1.0 - alpha) * grav_state["bz"] + alpha * az_g

    dx = ax_g - grav_state["bx"]
    dy = ay_g - grav_state["by"]
    dz = az_g - grav_state["bz"]
    dyn_mag = math.sqrt(dx * dx + dy * dy + dz * dz)

    window: List[float] = grav_state.setdefault("window", [])
    window.append(dyn_mag)
    if len(window) > 10:
        window.pop(0)

    rms_g = math.sqrt(sum(v * v for v in window) / len(window))
    peak_g = max(window)

    # Track IR transitions in serial CSV mode
    prev_ir1 = grav_state.get("prev_ir1", ir1)
    prev_ir2 = grav_state.get("prev_ir2", ir2)
    if ir1 == 0 and prev_ir1 == 1:
        grav_state["ir1_events"] = grav_state.get("ir1_events", 0) + 1
    if ir2 == 0 and prev_ir2 == 1:
        grav_state["ir2_events"] = grav_state.get("ir2_events", 0) + 1
        if grav_state.get("ir1_events", 0) >= grav_state.get("ir2_events", 0):
            grav_state["vehicle_count"] = grav_state.get("vehicle_count", 0) + 1
            grav_state["last_direction"] = "1_to_2"
    grav_state["prev_ir1"] = ir1
    grav_state["prev_ir2"] = ir2
    grav_state["seq"] = grav_state.get("seq", 0) + 1

    return {
        "device_id": "esp32-bridge-01",
        "seq": grav_state["seq"],
        "uptime_ms": uptime_ms,
        "imu_who_am_i": 104,
        "vibration_rms_g": rms_g,
        "vibration_peak_g": peak_g,
        "ax_g": ax_g,
        "ay_g": ay_g,
        "az_g": az_g,
        "gx_dps": gx_dps,
        "gy_dps": gy_dps,
        "gz_dps": gz_dps,
        "hx711_raw_counts": hx_raw,
        "hx711_net_counts": hx_net,
        "hx711_filtered_counts": hx_filtered,
        "hx711_calibrated": False,
        "calibration_factor": 0.0,
        "load_grams": None,
        "ir1_state": ir1,
        "ir2_state": ir2,
        "ir1_events": grav_state.get("ir1_events", 0),
        "ir2_events": grav_state.get("ir2_events", 0),
        "vehicle_count": grav_state.get("vehicle_count", 0),
        "last_direction": grav_state.get("last_direction", "none"),
        "last_crossing_ms": 0,
        "last_speed_mps": None,
    }


def record_from_mqtt(args: argparse.Namespace, target_csv: Path) -> List[Dict[str, Any]]:
    """Record live telemetry from the Mosquitto MQTT broker."""
    import paho.mqtt.client as mqtt

    rows: List[Dict[str, Any]] = []
    stop_requested = False

    def _sig_handler(signum: int, frame: Any) -> None:
        nonlocal stop_requested
        print("\n[INFO] Stop requested (Ctrl+C) — finishing and saving recorded rows...")
        stop_requested = True

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    def _on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: Any, props: Any = None) -> None:
        if rc == 0:
            print(f"[MQTT] Connected to {args.mqtt_host}:{args.mqtt_port} | Subscribed to '{args.mqtt_topic}'")
            client.subscribe(args.mqtt_topic)
        else:
            print(f"[MQTT] Connect failed with code {rc}")

    def _on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            validated = parse_and_validate_payload(msg.payload)
            row = build_csv_row_from_telemetry(
                raw_dict=validated.raw_dict,
                run_id=args.run_id,
                condition=args.condition,
                data_source=args.data_source,
                applied_mass_g=args.applied_mass_g,
                load_position=args.load_position,
                notes=args.notes,
                timestamp_iso=validated.server_timestamp.isoformat(),
            )
            rows.append(row)
            print(
                f"  [{len(rows):03d}] ts={row['timestamp']} | rms={row['vibration_rms_g']:.4f}g "
                f"| peak={row['vibration_peak_g']:.4f}g | hx_filt={row['hx711_filtered_counts']} "
                f"| veh={row['vehicle_count']}"
            )
        except TelemetryValidationError as exc:
            print(f"  [WARN] Ignored malformed MQTT message: {exc}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if args.mqtt_username:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)
    client.on_connect = _on_connect
    client.on_message = _on_message

    client.connect(args.mqtt_host, args.mqtt_port, keepalive=30)
    client.loop_start()

    start_time = time.time()
    try:
        while not stop_requested and (time.time() - start_time) < args.duration:
            time.sleep(0.2)
    finally:
        client.loop_stop()
        client.disconnect()

    if rows:
        write_rows_to_csv(target_csv, rows)
    return rows


def record_from_serial(args: argparse.Namespace, target_csv: Path) -> List[Dict[str, Any]]:
    """Record live telemetry directly from the ESP32 USB Serial port."""
    import serial

    rows: List[Dict[str, Any]] = []
    grav_state: Dict[str, Any] = {}
    stop_requested = False

    def _sig_handler(signum: int, frame: Any) -> None:
        nonlocal stop_requested
        print("\n[INFO] Stop requested (Ctrl+C) — closing serial port and saving CSV...")
        stop_requested = True

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    print(f"[SERIAL] Opening {args.serial_port} at {args.serial_baud} baud...")
    with serial.Serial(args.serial_port, args.serial_baud, timeout=1.0) as ser:
        start_time = time.time()
        while not stop_requested and (time.time() - start_time) < args.duration:
            raw_line = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw_line:
                continue

            parsed_dict: Optional[Dict[str, Any]] = None
            if raw_line.startswith("{") and raw_line.endswith("}"):
                try:
                    validated = parse_and_validate_payload(raw_line)
                    parsed_dict = validated.raw_dict
                except TelemetryValidationError:
                    continue
            else:
                parsed_dict = parse_serial_csv_line(raw_line, grav_state)

            if parsed_dict is not None:
                row = build_csv_row_from_telemetry(
                    raw_dict=parsed_dict,
                    run_id=args.run_id,
                    condition=args.condition,
                    data_source=args.data_source,
                    applied_mass_g=args.applied_mass_g,
                    load_position=args.load_position,
                    notes=args.notes,
                )
                rows.append(row)
                if len(rows) == 1 or len(rows) % 10 == 0:
                    print(
                        f"  [{len(rows):03d}] uptime={row['uptime_ms']}ms | rms={row['vibration_rms_g']:.4f}g "
                        f"| hx_filt={row['hx711_filtered_counts']} | ir={row['ir1_state']}/{row['ir2_state']}"
                    )

    if rows:
        write_rows_to_csv(target_csv, rows)
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record an experimental trial from MQTT or USB Serial into CSV."
    )
    default_run_id = f"EXP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    parser.add_argument("--run-id", default=default_run_id, help="Unique trial run identifier")
    parser.add_argument(
        "--condition",
        required=True,
        choices=ALLOWED_CONDITIONS,
        help="Experimental condition label (baseline, static_load, vehicle_crossing)",
    )
    parser.add_argument(
        "--applied-mass-g",
        type=float,
        default=0.0,
        help="Known static mass applied in grams (0 for baseline/vehicle_crossing)",
    )
    parser.add_argument(
        "--load-position",
        default="unloaded",
        help="Load position or crossing direction note (e.g., mid-span, support-end, 1_to_2)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Recording duration in seconds (can stop early with Ctrl+C)",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Free-text experiment notes stored with every row",
    )
    parser.add_argument(
        "--mode",
        choices=("mqtt", "serial"),
        default="mqtt",
        help="Capture source: 'mqtt' (default) or 'serial'",
    )
    parser.add_argument(
        "--data-source",
        choices=("experimental", "synthetic"),
        default="experimental",
        help="Dataset classification (experimental writes to data/experimental/, synthetic to data/sample/)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional custom output directory override",
    )
    parser.add_argument(
        "--mqtt-host",
        default=os.getenv("MQTT_BROKER_HOST", "localhost"),
        help="MQTT broker host",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
        help="MQTT broker port",
    )
    parser.add_argument(
        "--mqtt-username",
        default=os.getenv("MQTT_USERNAME", "bridge_iot"),
        help="MQTT username",
    )
    parser.add_argument(
        "--mqtt-password",
        default=os.getenv("MQTT_PASSWORD", "bridge_iot_pass"),
        help="MQTT password",
    )
    parser.add_argument(
        "--mqtt-topic",
        default=os.getenv("MQTT_TOPIC", "structural-health/+/telemetry"),
        help="MQTT telemetry topic filter",
    )
    parser.add_argument(
        "--serial-port",
        default=os.getenv("SERIAL_PORT", "COM3"),
        help="Serial port for --mode serial (e.g. COM3)",
    )
    parser.add_argument(
        "--serial-baud",
        type=int,
        default=int(os.getenv("SERIAL_BAUD", "115200")),
        help="Serial baud rate (default: 115200)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif args.data_source == "synthetic":
        out_dir = REPO_ROOT / "data" / "sample"
    else:
        out_dir = REPO_ROOT / "data" / "experimental"

    target_csv = resolve_non_overwriting_csv_path(out_dir, args.run_id, args.condition)

    print("============================================================")
    print(" STRUCTURAL HEALTH IoT — EXPERIMENTAL TRIAL RECORDER")
    print("============================================================")
    print(f"  Run ID        : {args.run_id}")
    print(f"  Condition     : {args.condition}")
    print(f"  Data Source   : {args.data_source}")
    print(f"  Applied Mass  : {args.applied_mass_g:.2f} g")
    print(f"  Load Position : {args.load_position}")
    print(f"  Duration      : {args.duration:.1f} s (press Ctrl+C to stop early)")
    print(f"  Capture Mode  : {args.mode}")
    print(f"  Target CSV    : {target_csv}")
    print("============================================================")

    if args.mode == "mqtt":
        rows = record_from_mqtt(args, target_csv)
    else:
        rows = record_from_serial(args, target_csv)

    print("============================================================")
    if rows:
        print(f"[SUCCESS] Saved {len(rows)} samples to: {target_csv}")
    else:
        print("[WARNING] No telemetry samples received during window (no CSV created).")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
