"""Dataset validation, cleaning, and feature extraction — Structural Health IoT Analytics.

Strictly uses the 3 active hardware sensor groups:
  1. IMU (vibration_rms_g, vibration_peak_g, accelerometer & gyroscope variation)
  2. Load Cell + HX711 (hx711_net_counts, hx711_filtered_counts; optional load_grams)
  3. Dual IR Obstacle Sensors (ir1_state, ir2_state, ir1_events, ir2_events, vehicle_count)

NOTE: VL53L0X ToF (`deflection_mm`) has been officially dropped and is explicitly
excluded from all schemas and ML feature vectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ALLOWED_CONDITIONS = ("baseline", "static_load", "vehicle_crossing")

REQUIRED_RAW_COLUMNS = (
    "timestamp",
    "run_id",
    "condition",
    "vibration_rms_g",
    "vibration_peak_g",
    "ax_g",
    "ay_g",
    "az_g",
    "gx_dps",
    "gy_dps",
    "gz_dps",
    "hx711_net_counts",
    "hx711_filtered_counts",
    "ir1_state",
    "ir2_state",
    "ir1_events",
    "ir2_events",
    "vehicle_count",
)

# Core interpretable ML feature set available across both calibrated and uncalibrated runs
ML_FEATURE_COLUMNS = [
    "vibration_rms_g",
    "vibration_peak_g",
    "accel_dynamic_g",
    "gyro_magnitude_dps",
    "hx711_filtered_counts",
    "ir_blocked_sensors",
    "ir_event_rate",
    "vehicle_crossing_delta",
]


@dataclass
class DatasetReadinessReport:
    """Assesses whether a loaded dataset meets minimum statistical requirements for ML evaluation."""

    is_ready_for_group_ml: bool
    total_samples: int
    num_classes: int
    classes_present: List[str]
    runs_per_class: Dict[str, int]
    data_sources: List[str]
    reasons: List[str]


def load_csv_files(path_or_dir: Path | str) -> pd.DataFrame:
    """Load a single CSV file or all CSV files inside a directory."""
    target = Path(path_or_dir)
    if target.is_dir():
        csv_paths = sorted(target.glob("*.csv"))
    elif target.is_file():
        csv_paths = [target]
    else:
        raise FileNotFoundError(f"Dataset path does not exist: {target}")

    if not csv_paths:
        raise ValueError(f"No CSV files found in: {target}")

    frames: List[pd.DataFrame] = []
    for csv_path in csv_paths:
        df_part = pd.read_csv(csv_path)
        df_part["_source_file"] = csv_path.name
        frames.append(df_part)

    return pd.concat(frames, ignore_index=True)


def validate_and_clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate schema, remove deprecated ToF columns, coerce numeric types, and drop invalid rows."""
    if df.empty:
        raise ValueError("Loaded DataFrame is empty")

    work = df.copy()

    # Explicitly strip any legacy VL53L0X/ToF displacement columns if present
    for legacy_col in ("deflection_mm", "tof_mm", "vl53l0x_mm"):
        if legacy_col in work.columns:
            work = work.drop(columns=[legacy_col])

    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in work.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    work["run_id"] = work["run_id"].astype(str).str.strip()
    work["condition"] = work["condition"].astype(str).str.strip().str.lower()
    work = work[work["condition"].isin(ALLOWED_CONDITIONS)].copy()

    if "data_source" not in work.columns:
        work["data_source"] = np.where(
            work["run_id"].str.upper().str.startswith("SYNTH"),
            "synthetic",
            "experimental",
        )
    else:
        work["data_source"] = work["data_source"].fillna("experimental").astype(str).str.lower()

    numeric_cols = [
        "vibration_rms_g",
        "vibration_peak_g",
        "ax_g",
        "ay_g",
        "az_g",
        "gx_dps",
        "gy_dps",
        "gz_dps",
        "hx711_net_counts",
        "hx711_filtered_counts",
        "ir1_state",
        "ir2_state",
        "ir1_events",
        "ir2_events",
        "vehicle_count",
    ]
    for col in numeric_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    # Replace +/-inf with NaN and drop rows missing core sensor readings
    work.replace([np.inf, -np.inf], np.nan, inplace=True)
    work.dropna(subset=numeric_cols + ["run_id", "condition"], inplace=True)

    # Filter out physically impossible negative vibration magnitudes
    work = work[(work["vibration_rms_g"] >= 0.0) & (work["vibration_peak_g"] >= 0.0)].copy()

    # Parse timestamps and sort chronologically within each run_id
    work["parsed_timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    if "seq" in work.columns:
        work["seq"] = pd.to_numeric(work["seq"], errors="coerce").fillna(0).astype(int)
        work.sort_values(by=["run_id", "parsed_timestamp", "seq"], inplace=True)
    else:
        work.sort_values(by=["run_id", "parsed_timestamp"], inplace=True)

    work.reset_index(drop=True, inplace=True)
    if work.empty:
        raise ValueError("No valid rows remained after cleaning and validation")

    return work


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute interpretable domain features per trial (`run_id`) without data leakage."""
    work = validate_and_clean_dataframe(df)

    # 1. Dynamic 3-axis acceleration deviation from static 1g gravity vector
    accel_norm = np.sqrt(work["ax_g"] ** 2 + work["ay_g"] ** 2 + work["az_g"] ** 2)
    work["accel_dynamic_g"] = np.abs(accel_norm - 1.0)

    # 2. 3-axis angular velocity magnitude (deg/s)
    work["gyro_magnitude_dps"] = np.sqrt(
        work["gx_dps"] ** 2 + work["gy_dps"] ** 2 + work["gz_dps"] ** 2
    )

    # 3. Number of currently blocked IR sensors (active-LOW: 0 means blocked)
    ir1_blocked = (work["ir1_state"] == 0).astype(int)
    ir2_blocked = (work["ir2_state"] == 0).astype(int)
    work["ir_blocked_sensors"] = ir1_blocked + ir2_blocked

    # 4. Within-run IR event and vehicle crossing increments (rolling 3-sample window inside each run)
    work["ir_total_events"] = work["ir1_events"] + work["ir2_events"]
    work["ir_event_rate"] = (
        work.groupby("run_id")["ir_total_events"]
        .diff()
        .fillna(0.0)
        .clip(lower=0.0)
        .groupby(work["run_id"])
        .transform(lambda s: s.rolling(window=5, min_periods=1).sum())
    )
    work["vehicle_crossing_delta"] = (
        work.groupby("run_id")["vehicle_count"]
        .diff()
        .fillna(0.0)
        .clip(lower=0.0)
        .groupby(work["run_id"])
        .transform(lambda s: s.rolling(window=5, min_periods=1).sum())
    )

    return work


def assess_ml_readiness(df: pd.DataFrame, min_runs_per_class: int = 2) -> DatasetReadinessReport:
    """Check if the dataset has enough classes and independent runs for valid group-split evaluation."""
    classes_present = sorted(df["condition"].unique().tolist())
    runs_per_class: Dict[str, int] = {}
    for cls in classes_present:
        runs_per_class[cls] = int(df.loc[df["condition"] == cls, "run_id"].nunique())

    data_sources = sorted(df["data_source"].unique().tolist()) if "data_source" in df.columns else ["unknown"]
    reasons: List[str] = []

    if len(classes_present) < 2:
        reasons.append(
            f"Only {len(classes_present)} condition class present ({classes_present}); at least 2 classes are required."
        )
    for cls, n_runs in runs_per_class.items():
        if n_runs < min_runs_per_class:
            reasons.append(
                f"Condition '{cls}' has only {n_runs} independent run(s); at least {min_runs_per_class} independent runs per class are required for group-aware train/test splitting."
            )
    if len(df) < 20:
        reasons.append(f"Total sample count ({len(df)}) is below the minimum of 20 samples.")

    return DatasetReadinessReport(
        is_ready_for_group_ml=(len(reasons) == 0),
        total_samples=len(df),
        num_classes=len(classes_present),
        classes_present=classes_present,
        runs_per_class=runs_per_class,
        data_sources=data_sources,
        reasons=reasons,
    )


def extract_single_sample_features(sample: Dict[str, float]) -> pd.DataFrame:
    """Convert a single observation dictionary into a 1-row DataFrame matching ML_FEATURE_COLUMNS."""
    vib_rms = float(sample.get("vibration_rms_g", 0.0))
    vib_peak = float(sample.get("vibration_peak_g", 0.0))

    if "accel_dynamic_g" in sample:
        accel_dyn = float(sample["accel_dynamic_g"])
    else:
        ax = float(sample.get("ax_g", 0.0))
        ay = float(sample.get("ay_g", 0.0))
        az = float(sample.get("az_g", 1.0))
        accel_dyn = abs(float(np.sqrt(ax * ax + ay * ay + az * az)) - 1.0)

    if "gyro_magnitude_dps" in sample:
        gyro_mag = float(sample["gyro_magnitude_dps"])
    else:
        gx = float(sample.get("gx_dps", 0.0))
        gy = float(sample.get("gy_dps", 0.0))
        gz = float(sample.get("gz_dps", 0.0))
        gyro_mag = float(np.sqrt(gx * gx + gy * gy + gz * gz))

    hx_filt = float(
        sample.get("hx711_filtered_counts", sample.get("hx711_net_counts", 0.0))
    )

    if "ir_blocked_sensors" in sample:
        ir_blocked = float(sample["ir_blocked_sensors"])
    else:
        ir1 = int(sample.get("ir1_state", 1))
        ir2 = int(sample.get("ir2_state", 1))
        ir_blocked = float((1 if ir1 == 0 else 0) + (1 if ir2 == 0 else 0))

    ir_event_rate = float(sample.get("ir_event_rate", sample.get("ir1_events", 0) + sample.get("ir2_events", 0)))
    veh_delta = float(sample.get("vehicle_crossing_delta", sample.get("vehicle_count", 0)))

    row = {
        "vibration_rms_g": vib_rms,
        "vibration_peak_g": vib_peak,
        "accel_dynamic_g": accel_dyn,
        "gyro_magnitude_dps": gyro_mag,
        "hx711_filtered_counts": hx_filt,
        "ir_blocked_sensors": ir_blocked,
        "ir_event_rate": ir_event_rate,
        "vehicle_crossing_delta": veh_delta,
    }
    return pd.DataFrame([row], columns=ML_FEATURE_COLUMNS)
