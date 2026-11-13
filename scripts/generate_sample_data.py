"""Synthetic Demonstration Dataset Generator — Structural Health IoT Analytics.

Generates clearly labelled SYNTHETIC trial data under `data/sample/synthetic_trials.csv`
and updates `data/sample/sample-format.csv` for software testing, analytics verification,
and Decision Tree ML pipeline demonstration.

IMPORTANT DATA INTEGRITY RULE:
  - Every generated row has `data_source = "synthetic"` and `run_id` prefixed with `SYNTH_`.
  - Synthetic data is NEVER written to `data/experimental/` and must NEVER be presented
    as physical measurements from the tabletop bridge prototype.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.record_trial import CSV_COLUMNS, write_rows_to_csv  # noqa: E402


def generate_synthetic_dataset(seed: int = 42, samples_per_run: int = 20) -> List[Dict[str, Any]]:
    """Generate a reproducible multi-run synthetic dataset across 3 experimental conditions."""
    rng = np.random.default_rng(seed)
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)

    # 12 independent synthetic runs (4 per condition) to enable group-aware train/test splitting
    trial_specs = [
        ("SYNTH_RUN_01", "baseline", 0.0, "unloaded", "Synthetic unloaded baseline trial 1"),
        ("SYNTH_RUN_02", "baseline", 0.0, "unloaded", "Synthetic unloaded baseline trial 2"),
        ("SYNTH_RUN_03", "baseline", 0.0, "unloaded", "Synthetic unloaded baseline trial 3"),
        ("SYNTH_RUN_04", "baseline", 0.0, "unloaded", "Synthetic unloaded baseline trial 4"),
        ("SYNTH_RUN_05", "static_load", 50.0, "mid-span", "Synthetic 50g static load mid-span"),
        ("SYNTH_RUN_06", "static_load", 100.0, "mid-span", "Synthetic 100g static load mid-span"),
        ("SYNTH_RUN_07", "static_load", 150.0, "near-support", "Synthetic 150g static load near support"),
        ("SYNTH_RUN_08", "static_load", 200.0, "mid-span", "Synthetic 200g static load mid-span"),
        ("SYNTH_RUN_09", "vehicle_crossing", 0.0, "1_to_2", "Synthetic toy car crossing 1->2 trial 1"),
        ("SYNTH_RUN_10", "vehicle_crossing", 0.0, "2_to_1", "Synthetic toy car crossing 2->1 trial 2"),
        ("SYNTH_RUN_11", "vehicle_crossing", 0.0, "1_to_2", "Synthetic toy car crossing 1->2 trial 3"),
        ("SYNTH_RUN_12", "vehicle_crossing", 0.0, "2_to_1", "Synthetic toy car crossing 2->1 trial 4"),
    ]

    rows: List[Dict[str, Any]] = []
    hx_zero = -381709
    seq_counter = 0

    for run_idx, (run_id, condition, mass_g, pos, note) in enumerate(trial_specs):
        run_start = base_time + timedelta(minutes=run_idx * 5)
        ir1_events = 0
        ir2_events = 0
        vehicle_count = 0
        last_dir = "none"
        last_dt_ms = 0

        for step in range(samples_per_run):
            seq_counter += 1
            ts = run_start + timedelta(seconds=step)
            uptime_ms = (run_idx * samples_per_run + step + 1) * 1000

            if condition == "baseline":
                vib_rms = float(np.clip(rng.normal(0.011, 0.0025), 0.004, 0.022))
                vib_peak = float(np.clip(vib_rms * rng.uniform(2.1, 3.0), 0.010, 0.055))
                ax_g = float(rng.normal(0.005, 0.004))
                ay_g = float(rng.normal(-0.004, 0.004))
                az_g = float(rng.normal(0.998, 0.005))
                gx_dps = float(rng.normal(0.08, 0.15))
                gy_dps = float(rng.normal(-0.06, 0.15))
                gz_dps = float(rng.normal(0.04, 0.12))
                hx_net = int(rng.normal(0, 35))
                hx_filt = float(hx_net + rng.normal(0, 10))
                ir1_state = 1
                ir2_state = 1

            elif condition == "static_load":
                # Low vibration at rest, elevated HX711 net/filtered counts from static load
                vib_rms = float(np.clip(rng.normal(0.013, 0.003), 0.005, 0.026))
                vib_peak = float(np.clip(vib_rms * rng.uniform(2.2, 3.2), 0.012, 0.065))
                ax_g = float(rng.normal(0.008, 0.005))
                ay_g = float(rng.normal(-0.006, 0.005))
                az_g = float(rng.normal(0.997, 0.006))
                gx_dps = float(rng.normal(0.10, 0.18))
                gy_dps = float(rng.normal(-0.09, 0.18))
                gz_dps = float(rng.normal(0.05, 0.15))
                # Reaction fraction depends on placement (mid-span ~0.5, near-support ~0.75)
                reaction_factor = 0.75 if pos == "near-support" else 0.52
                expected_counts = mass_g * reaction_factor * 255.0
                hx_net = int(rng.normal(expected_counts, 95))
                hx_filt = float(hx_net + rng.normal(0, 25))
                ir1_state = 1
                ir2_state = 1

            else:  # vehicle_crossing
                # Dynamic vibration excitation + periodic IR gate transitions + transient support reaction
                crossing_active = (step % 5 in (1, 2))
                if step % 5 == 1:
                    ir1_events += 1
                if step % 5 == 2:
                    ir2_events += 1
                    vehicle_count += 1
                    last_dir = pos if pos in ("1_to_2", "2_to_1") else "1_to_2"
                    last_dt_ms = int(rng.integers(380, 720))

                if crossing_active:
                    vib_rms = float(np.clip(rng.normal(0.072, 0.015), 0.042, 0.140))
                    vib_peak = float(np.clip(vib_rms * rng.uniform(2.5, 3.6), 0.110, 0.380))
                    gx_dps = float(rng.normal(1.8, 0.9))
                    gy_dps = float(rng.normal(-2.1, 1.1))
                    gz_dps = float(rng.normal(0.9, 0.5))
                    hx_net = int(rng.normal(4800, 650))
                    ir1_state = 0 if (step % 5 == 1) else 1
                    ir2_state = 0 if (step % 5 == 2) else 1
                else:
                    vib_rms = float(np.clip(rng.normal(0.038, 0.008), 0.024, 0.065))
                    vib_peak = float(np.clip(vib_rms * rng.uniform(2.3, 3.1), 0.065, 0.160))
                    gx_dps = float(rng.normal(0.6, 0.4))
                    gy_dps = float(rng.normal(-0.7, 0.4))
                    gz_dps = float(rng.normal(0.3, 0.25))
                    hx_net = int(rng.normal(1200, 300))
                    ir1_state = 1
                    ir2_state = 1

                ax_g = float(rng.normal(0.018, 0.025))
                ay_g = float(rng.normal(-0.015, 0.025))
                az_g = float(rng.normal(0.995, 0.035))
                hx_filt = float(hx_net + rng.normal(0, 45))

            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "run_id": run_id,
                    "condition": condition,
                    "data_source": "synthetic",
                    "device_id": "esp32-bridge-synthetic",
                    "seq": seq_counter,
                    "uptime_ms": uptime_ms,
                    "imu_who_am_i": 112,
                    "vibration_rms_g": round(vib_rms, 5),
                    "vibration_peak_g": round(vib_peak, 5),
                    "ax_g": round(ax_g, 4),
                    "ay_g": round(ay_g, 4),
                    "az_g": round(az_g, 4),
                    "gx_dps": round(gx_dps, 3),
                    "gy_dps": round(gy_dps, 3),
                    "gz_dps": round(gz_dps, 3),
                    "hx711_raw_counts": hx_zero + hx_net,
                    "hx711_net_counts": hx_net,
                    "hx711_filtered_counts": round(hx_filt, 2),
                    "hx711_calibrated": False,
                    "calibration_factor": 0.0,
                    "load_grams": "",
                    "ir1_state": ir1_state,
                    "ir2_state": ir2_state,
                    "ir1_events": ir1_events,
                    "ir2_events": ir2_events,
                    "vehicle_count": vehicle_count,
                    "last_direction": last_dir,
                    "last_crossing_ms": last_dt_ms,
                    "last_speed_mps": "",
                    "applied_mass_g": round(mass_g, 2),
                    "load_position": pos,
                    "notes": f"[SYNTHETIC DEMO DATA] {note}",
                }
            )

    return rows


def main() -> int:
    sample_dir = REPO_ROOT / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)

    rows = generate_synthetic_dataset(seed=42, samples_per_run=20)
    full_path = sample_dir / "synthetic_trials.csv"
    write_rows_to_csv(full_path, rows)

    # Also write a compact 6-row sample-format.csv illustrating the exact schema
    preview_rows = [rows[0], rows[1], rows[80], rows[81], rows[161], rows[162]]
    format_path = sample_dir / "sample-format.csv"
    write_rows_to_csv(format_path, preview_rows)

    print(f"[OK] Wrote {len(rows)} synthetic demonstration rows to {full_path}")
    print(f"[OK] Updated schema example in {format_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
