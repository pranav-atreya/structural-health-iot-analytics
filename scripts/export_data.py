"""InfluxDB-to-CSV Data Exporter & Dataset Inspector — Structural Health IoT Analytics.

Exports stored `bridge_telemetry` records from InfluxDB 2.x into the project's
standard CSV schema, or inspects/summarises existing CSV datasets.

Usage examples:
  # Export last 30 minutes of telemetry from InfluxDB
  python scripts/export_data.py --last 30m --run-id EXP_EXPORT_01 --condition baseline

  # Inspect and summarise any CSV dataset or directory
  python scripts/export_data.py --inspect data/sample/synthetic_trials.csv
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.record_trial import (  # noqa: E402
    CSV_COLUMNS,
    resolve_non_overwriting_csv_path,
    write_rows_to_csv,
)

load_dotenv(REPO_ROOT / ".env")


def export_influx_to_csv(
    influx_url: str,
    influx_token: str,
    influx_org: str,
    influx_bucket: str,
    time_range: str,
    run_id: str,
    condition: str,
    applied_mass_g: float,
    load_position: str,
    notes: str,
    output_dir: Path,
    device_id: Optional[str] = None,
    data_source_filter: Optional[str] = None,
) -> Optional[Path]:
    """Query InfluxDB 2.x using Flux pivot and save rows to a non-overwriting CSV."""
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org, timeout=15_000)
    query_api = client.query_api()

    dev_filter = f' and r["device_id"] == "{device_id}"' if device_id else ""
    src_filter = f' and r["data_source"] == "{data_source_filter}"' if data_source_filter else ""

    flux_query = f"""
from(bucket: "{influx_bucket}")
  |> range(start: -{time_range.lstrip("-")})
  |> filter(fn: (r) => r["_measurement"] == "bridge_telemetry"{dev_filter}{src_filter})
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: false)
"""
    tables = query_api.query(flux_query, org=influx_org)
    client.close()

    rows: List[Dict[str, Any]] = []
    for table in tables:
        for record in table.records:
            vals = record.values
            ts = record.get_time()
            ts_iso = ts.astimezone(timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat()
            hx_cal = str(vals.get("calibrated", "false")).lower() == "true" or bool(
                vals.get("hx711_calibrated", False)
            )
            load_g = vals.get("load_grams", "")
            if not hx_cal or load_g is None:
                load_g = ""

            speed_mps = vals.get("last_speed_mps", "")
            if speed_mps is None:
                speed_mps = ""

            row = {
                "timestamp": ts_iso,
                "run_id": run_id,
                "condition": condition,
                "data_source": vals.get("data_source", "experimental"),
                "device_id": vals.get("device_id", "esp32-bridge-01"),
                "seq": int(vals.get("seq", 0) or 0),
                "uptime_ms": int(vals.get("uptime_ms", 0) or 0),
                "imu_who_am_i": int(vals.get("imu_who_am_i", 104) or 104),
                "vibration_rms_g": round(float(vals.get("vibration_rms_g", 0.0) or 0.0), 5),
                "vibration_peak_g": round(float(vals.get("vibration_peak_g", 0.0) or 0.0), 5),
                "ax_g": round(float(vals.get("ax_g", 0.0) or 0.0), 4),
                "ay_g": round(float(vals.get("ay_g", 0.0) or 0.0), 4),
                "az_g": round(float(vals.get("az_g", 1.0) or 1.0), 4),
                "gx_dps": round(float(vals.get("gx_dps", 0.0) or 0.0), 3),
                "gy_dps": round(float(vals.get("gy_dps", 0.0) or 0.0), 3),
                "gz_dps": round(float(vals.get("gz_dps", 0.0) or 0.0), 3),
                "hx711_raw_counts": int(vals.get("hx711_raw_counts", 0) or 0),
                "hx711_net_counts": int(vals.get("hx711_net_counts", 0) or 0),
                "hx711_filtered_counts": round(float(vals.get("hx711_filtered_counts", 0.0) or 0.0), 2),
                "hx711_calibrated": hx_cal,
                "calibration_factor": round(float(vals.get("calibration_factor", 0.0) or 0.0), 4),
                "load_grams": load_g,
                "ir1_state": int(vals.get("ir1_state", 1) if vals.get("ir1_state") is not None else 1),
                "ir2_state": int(vals.get("ir2_state", 1) if vals.get("ir2_state") is not None else 1),
                "ir1_events": int(vals.get("ir1_events", 0) or 0),
                "ir2_events": int(vals.get("ir2_events", 0) or 0),
                "vehicle_count": int(vals.get("vehicle_count", 0) or 0),
                "last_direction": str(vals.get("last_direction") or vals.get("last_direction_str") or "none"),
                "last_crossing_ms": int(vals.get("last_crossing_ms", 0) or 0),
                "last_speed_mps": speed_mps,
                "applied_mass_g": round(float(applied_mass_g), 2),
                "load_position": load_position,
                "notes": notes,
            }
            rows.append(row)

    if not rows:
        return None

    target_csv = resolve_non_overwriting_csv_path(output_dir, run_id, condition)
    write_rows_to_csv(target_csv, rows)
    return target_csv


def inspect_and_summarize_dataset(target_path: Path) -> Dict[str, Any]:
    """Load one CSV or a directory of CSVs and return/print trial summary statistics."""
    if target_path.is_dir():
        csv_files = sorted(target_path.glob("*.csv"))
    elif target_path.is_file():
        csv_files = [target_path]
    else:
        raise FileNotFoundError(f"Path not found: {target_path}")

    if not csv_files:
        raise ValueError(f"No CSV files found in {target_path}")

    frames = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    missing_cols = [c for c in ("timestamp", "run_id", "condition", "vibration_rms_g") if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing required columns: {missing_cols}")

    if "deflection_mm" in df.columns:
        raise ValueError("Dataset contains deprecated ToF 'deflection_mm' column!")

    summary_by_run = (
        df.groupby(["run_id", "condition"], dropna=False)
        .agg(
            samples=("timestamp", "count"),
            mean_vib_rms_g=("vibration_rms_g", "mean"),
            max_vib_peak_g=("vibration_peak_g", "max"),
            mean_hx_net=("hx711_net_counts", "mean"),
            max_vehicle_count=("vehicle_count", "max"),
        )
        .reset_index()
    )

    print("============================================================")
    print(f" DATASET INSPECTION SUMMARY: {target_path}")
    print("============================================================")
    print(f"  Files loaded      : {len(csv_files)}")
    print(f"  Total samples     : {len(df)}")
    print(f"  Distinct runs     : {df['run_id'].nunique()}")
    print(f"  Conditions        : {sorted(df['condition'].dropna().unique().tolist())}")
    if "data_source" in df.columns:
        print(f"  Data sources      : {sorted(df['data_source'].dropna().unique().tolist())}")
    print("\nPer-Run Trial Summary:")
    print(summary_by_run.to_string(index=False))
    print("============================================================")

    return {
        "files_count": len(csv_files),
        "total_rows": len(df),
        "unique_runs": int(df["run_id"].nunique()),
        "conditions": sorted(df["condition"].dropna().unique().tolist()),
        "summary_records": summary_by_run.to_dict(orient="records"),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export InfluxDB telemetry to CSV or inspect/summarise existing datasets."
    )
    parser.add_argument(
        "--inspect",
        default=None,
        help="Path to a CSV file or directory to inspect and summarise instead of querying InfluxDB",
    )
    parser.add_argument("--last", default="30m", help="Relative Flux range to export (e.g. 15m, 1h, 24h)")
    parser.add_argument("--run-id", default=f"EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--condition", default="baseline", choices=("baseline", "static_load", "vehicle_crossing"))
    parser.add_argument("--applied-mass-g", type=float, default=0.0)
    parser.add_argument("--load-position", default="unloaded")
    parser.add_argument("--notes", default="Exported from InfluxDB")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--data-source", default=None)
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "data" / "experimental"))
    parser.add_argument("--influx-url", default=os.getenv("INFLUXDB_URL", "http://localhost:8086"))
    parser.add_argument(
        "--influx-token",
        default=os.getenv("INFLUXDB_TOKEN", "structural-health-iot-local-dev-token-2026"),
    )
    parser.add_argument("--influx-org", default=os.getenv("INFLUXDB_ORG", "pes-iot"))
    parser.add_argument("--influx-bucket", default=os.getenv("INFLUXDB_BUCKET", "structural_health"))
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.inspect:
        inspect_and_summarize_dataset(Path(args.inspect))
        return 0

    csv_path = export_influx_to_csv(
        influx_url=args.influx_url,
        influx_token=args.influx_token,
        influx_org=args.influx_org,
        influx_bucket=args.influx_bucket,
        time_range=args.last,
        run_id=args.run_id,
        condition=args.condition,
        applied_mass_g=args.applied_mass_g,
        load_position=args.load_position,
        notes=args.notes,
        output_dir=Path(args.output_dir),
        device_id=args.device_id,
        data_source_filter=args.data_source,
    )
    if csv_path:
        print(f"[SUCCESS] Exported InfluxDB telemetry to: {csv_path}")
        inspect_and_summarize_dataset(csv_path)
    else:
        print("[WARNING] No matching records found in InfluxDB for the requested time window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
