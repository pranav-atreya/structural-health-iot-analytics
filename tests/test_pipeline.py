"""Comprehensive Unit & Integration Test Suite — Structural Health IoT Analytics.

Tests:
  1. MQTT JSON payload parsing and validation (`backend.mqtt_ingestor.validator`)
  2. Rejection of malformed JSON, NaN/Infinity, negative vibration, and legacy ToF fields
  3. InfluxDB Point & Line Protocol generation (including uncalibrated vs calibrated load cell)
  4. Serial 10 Hz CSV parsing, trial CSV recording, and non-overwriting file resolution
  5. Load-cell calibration factor computation (`scripts.calibrate_load_cell`)
  6. Synthetic dataset generation (`scripts.generate_sample_data`)
  7. Analytics feature engineering & summary generation (`analytics-ml/preprocess.py`, `analyze_trials.py`)
  8. Decision Tree ML group-aware splitting by `run_id`, readiness check on insufficient data,
     model training, evaluation metrics, and single/batch prediction (`train_model.py`, `predict.py`)
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = REPO_ROOT / "analytics-ml"
for p in (str(REPO_ROOT), str(ANALYTICS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.mqtt_ingestor.validator import (  # noqa: E402
    TelemetryValidationError,
    parse_and_validate_payload,
    validate_and_build_point,
)
from scripts.calibrate_load_cell import compute_calibration_factor  # noqa: E402
from scripts.export_data import inspect_and_summarize_dataset  # noqa: E402
from scripts.generate_sample_data import generate_synthetic_dataset  # noqa: E402
from scripts.record_trial import (  # noqa: E402
    CSV_COLUMNS,
    build_csv_row_from_telemetry,
    parse_serial_csv_line,
    resolve_non_overwriting_csv_path,
    write_rows_to_csv,
)
from preprocess import (  # noqa: E402
    ML_FEATURE_COLUMNS,
    assess_ml_readiness,
    engineer_features,
)
from analyze_trials import run_analysis  # noqa: E402
from train_model import split_by_independent_runs, train_and_evaluate  # noqa: E402
from predict import predict_single_observation  # noqa: E402


# ============================================================================
# 1. MQTT PAYLOAD PARSING, VALIDATION & INFLUXDB POINT CREATION TESTS
# ============================================================================


def test_valid_uncalibrated_payload_creates_influx_point() -> None:
    payload = {
        "device_id": "esp32-bridge-01",
        "uptime_ms": 120000,
        "imu_who_am_i": 112,
        "vibration_rms_g": 0.025,
        "vibration_peak_g": 0.081,
        "ax_g": 0.01,
        "ay_g": 0.02,
        "az_g": 0.99,
        "gx_dps": 0.2,
        "gy_dps": -0.1,
        "gz_dps": 0.3,
        "hx711_calibrated": False,
        "hx711_raw_counts": -381709,
        "hx711_net_counts": -70,
        "hx711_filtered_counts": -23.5,
        "load_grams": None,
        "ir1_state": 1,
        "ir2_state": 1,
        "ir1_events": 0,
        "ir2_events": 0,
        "vehicle_count": 0,
    }
    ts = datetime(2026, 11, 12, 8, 30, 0, tzinfo=timezone.utc)
    validated, point = validate_and_build_point(json.dumps(payload), server_timestamp=ts)

    assert validated.device_id == "esp32-bridge-01"
    assert validated.tags["imu_chip"] == "0x70_MPU6500"
    assert validated.tags["calibrated"] == "false"
    assert "load_grams" not in validated.fields
    assert validated.fields["hx711_raw_counts"] == -381709
    assert validated.fields["hx711_net_counts"] == -70
    assert validated.fields["vibration_rms_g"] == pytest.approx(0.025)

    line_proto = point.to_line_protocol()
    assert line_proto.startswith("bridge_telemetry,")
    assert "device_id=esp32-bridge-01" in line_proto
    assert "imu_chip=0x70_MPU6500" in line_proto
    assert "vibration_rms_g=0.025" in line_proto
    assert "load_grams" not in line_proto


def test_valid_calibrated_payload_with_mpu6050_id() -> None:
    payload = {
        "device_id": "esp32-bridge-01",
        "uptime_ms": 5000,
        "imu_who_am_i": 104,  # 0x68
        "vibration_rms_g": 0.015,
        "vibration_peak_g": 0.040,
        "hx711_calibrated": True,
        "calibration_factor": 256.6,
        "hx711_raw_counts": -356049,
        "hx711_net_counts": 25660,
        "hx711_filtered_counts": 25655.0,
        "load_grams": 100.0,
        "ir1_state": 0,
        "ir2_state": 1,
        "vehicle_count": 2,
        "last_direction": "1_to_2",
        "last_speed_mps": 0.42,
    }
    validated, point = validate_and_build_point(json.dumps(payload))
    assert validated.tags["imu_chip"] == "0x68_MPU6050"
    assert validated.tags["calibrated"] == "true"
    assert validated.fields["load_grams"] == pytest.approx(100.0)
    assert validated.fields["last_speed_mps"] == pytest.approx(0.42)
    assert "load_grams=100" in point.to_line_protocol()


def test_legacy_tof_deflection_field_is_stripped_automatically() -> None:
    payload = {
        "device_id": "esp32-bridge-01",
        "vibration_rms_g": 0.018,
        "deflection_mm": 0.45,
    }
    validated = parse_and_validate_payload(json.dumps(payload))
    assert "deflection_mm" not in validated.fields
    assert "deflection_mm" not in validated.raw_dict


@pytest.mark.parametrize(
    "bad_payload",
    [
        "",
        "{malformed json",
        "[]",
        '{"vibration_rms_g": 0.02}',  # missing device_id
        '{"device_id": "esp32-01", "vibration_rms_g": NaN}',
        '{"device_id": "esp32-01", "vibration_rms_g": Infinity}',
        '{"device_id": "esp32-01", "vibration_rms_g": -0.05}',  # negative RMS
        '{"device_id": "esp32-01", "ir1_state": 5}',  # invalid digital state
        '{"device_id": "esp32-01"}',  # no measurement fields
    ],
)
def test_invalid_payloads_are_rejected(bad_payload: str) -> None:
    with pytest.raises(TelemetryValidationError):
        parse_and_validate_payload(bad_payload)


# ============================================================================
# 2. CSV RECORDING, SERIAL PARSING & CALIBRATION TESTS
# ============================================================================


def test_non_overwriting_csv_path_never_clobbers_existing_file(tmp_path: Path) -> None:
    p1 = resolve_non_overwriting_csv_path(tmp_path, "EXP_01", "baseline")
    p1.write_text("header\n", encoding="utf-8")
    p2 = resolve_non_overwriting_csv_path(tmp_path, "EXP_01", "baseline")
    assert p1 != p2
    assert not p2.exists()


def test_serial_csv_line_parser_preserves_hardware_format() -> None:
    state: dict = {}
    line = "12500,0.0112,-0.0085,0.9961,0.152,-0.091,0.045,-381709,-45,-32.50,1,0"
    parsed = parse_serial_csv_line(line, state)
    assert parsed is not None
    assert parsed["uptime_ms"] == 12500
    assert parsed["hx711_raw_counts"] == -381709
    assert parsed["hx711_net_counts"] == -45
    assert parsed["hx711_filtered_counts"] == pytest.approx(-32.50)
    assert parsed["ir1_state"] == 1
    assert parsed["ir2_state"] == 0
    assert "deflection_mm" not in parsed

    row = build_csv_row_from_telemetry(
        raw_dict=parsed,
        run_id="EXP_SERIAL_01",
        condition="vehicle_crossing",
        data_source="experimental",
        applied_mass_g=0.0,
        load_position="1_to_2",
        notes="Unit test serial capture",
    )
    assert list(row.keys()) == CSV_COLUMNS
    assert "deflection_mm" not in row


def test_load_cell_calibration_calculation() -> None:
    res = compute_calibration_factor(
        known_mass_g=50.0,
        net_counts_samples=[12820.0, 12830.0, 12840.0],
        tare_counts=-381709.0,
    )
    assert res.net_counts == pytest.approx(12830.0)
    assert res.calibration_factor_counts_per_g == pytest.approx(256.6)
    assert res.std_net_counts == pytest.approx(10.0)


# ============================================================================
# 3. ANALYTICS & DECISION TREE ML PIPELINE TESTS
# ============================================================================


def test_synthetic_dataset_and_ml_pipeline_end_to_end(tmp_path: Path) -> None:
    rows = generate_synthetic_dataset(seed=42, samples_per_run=15)
    csv_path = tmp_path / "synthetic_trials.csv"
    write_rows_to_csv(csv_path, rows)

    summary = inspect_and_summarize_dataset(csv_path)
    assert summary["unique_runs"] == 12
    assert set(summary["conditions"]) == {"baseline", "static_load", "vehicle_crossing"}

    df_raw = pd.read_csv(csv_path)
    df_feat = engineer_features(df_raw)
    assert "deflection_mm" not in df_feat.columns
    for col in ML_FEATURE_COLUMNS:
        assert col in df_feat.columns

    # Verify group-aware splitting prevents any run_id overlap
    train_df, test_df, train_runs, test_runs = split_by_independent_runs(df_feat, seed=42)
    assert set(train_runs).isdisjoint(set(test_runs))
    assert set(train_df["run_id"]).isdisjoint(set(test_df["run_id"]))

    # Run full analytics and ML training
    results_dir = tmp_path / "results"
    ana_out = run_analysis(csv_path, results_dir)
    assert Path(ana_out["run_summary_path"]).exists()
    assert Path(ana_out["condition_summary_path"]).exists()

    ml_report = train_and_evaluate(csv_path, results_dir, seed=42)
    assert ml_report["status"] == "SUCCESS"
    assert ml_report["statistically_meaningful"] is True
    assert ml_report["is_synthetic_demonstration"] is True
    assert ml_report["metrics"]["accuracy"] >= 0.85

    model_path = results_dir / "decision_tree_model.joblib"
    assert model_path.exists()

    # Test single-observation prediction across all 3 operating conditions
    pred_base = predict_single_observation(
        model_path,
        {"vibration_rms_g": 0.010, "vibration_peak_g": 0.025, "hx711_filtered_counts": 5.0},
    )
    assert pred_base["predicted_condition"] == "baseline"

    pred_load = predict_single_observation(
        model_path,
        {"vibration_rms_g": 0.013, "vibration_peak_g": 0.032, "hx711_filtered_counts": 25000.0},
    )
    assert pred_load["predicted_condition"] == "static_load"

    pred_cross = predict_single_observation(
        model_path,
        {
            "vibration_rms_g": 0.080,
            "vibration_peak_g": 0.230,
            "hx711_filtered_counts": 4500.0,
            "ir1_state": 0,
            "ir_event_rate": 2.0,
            "vehicle_crossing_delta": 1.0,
        },
    )
    assert pred_cross["predicted_condition"] == "vehicle_crossing"


def test_ml_refuses_to_fabricate_evaluation_on_tiny_or_single_class_dataset(tmp_path: Path) -> None:
    rows = generate_synthetic_dataset(seed=42, samples_per_run=10)
    # Keep only 1 run of a single class ('baseline')
    tiny_rows = [r for r in rows if r["run_id"] == "SYNTH_RUN_01"]
    tiny_csv = tmp_path / "tiny.csv"
    write_rows_to_csv(tiny_csv, tiny_rows)

    report = train_and_evaluate(tiny_csv, tmp_path / "tiny_results", seed=42)
    assert report["status"] == "INSUFFICIENT_DATA_FOR_VALID_EVALUATION"
    assert report["statistically_meaningful"] is False
    assert len(report["reasons"]) >= 1
