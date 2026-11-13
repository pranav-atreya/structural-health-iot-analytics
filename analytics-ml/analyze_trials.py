"""Exploratory & Comparative Data Analysis — Structural Health IoT Analytics.

Loads experimental or synthetic trial CSVs, computes per-run and per-condition
summary statistics, and generates publication-ready comparative plots comparing
`baseline`, `static_load`, and `vehicle_crossing` operating conditions.

Usage:
  python analytics-ml/analyze_trials.py --data data/sample/synthetic_trials.csv
  python analytics-ml/analyze_trials.py --data data/experimental
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = Path(__file__).resolve().parent
for p in (str(REPO_ROOT), str(ANALYTICS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from preprocess import engineer_features, load_csv_files  # noqa: E402


def compute_summaries(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute per-run trial summary and per-condition aggregate summary tables."""
    run_summary = (
        df.groupby(["run_id", "condition", "data_source"], dropna=False)
        .agg(
            samples=("timestamp", "count"),
            vib_rms_mean_g=("vibration_rms_g", "mean"),
            vib_rms_std_g=("vibration_rms_g", "std"),
            vib_peak_max_g=("vibration_peak_g", "max"),
            gyro_mag_mean_dps=("gyro_magnitude_dps", "mean"),
            hx_net_mean_counts=("hx711_net_counts", "mean"),
            hx_filt_mean_counts=("hx711_filtered_counts", "mean"),
            ir_events_max=("ir_total_events", "max"),
            vehicle_crossings_max=("vehicle_count", "max"),
            applied_mass_g=("applied_mass_g", "max") if "applied_mass_g" in df.columns else ("seq", "count"),
        )
        .reset_index()
    )

    condition_summary = (
        df.groupby(["condition", "data_source"], dropna=False)
        .agg(
            num_runs=("run_id", "nunique"),
            total_samples=("timestamp", "count"),
            vib_rms_mean_g=("vibration_rms_g", "mean"),
            vib_rms_std_g=("vibration_rms_g", "std"),
            vib_peak_mean_g=("vibration_peak_g", "mean"),
            vib_peak_max_g=("vibration_peak_g", "max"),
            gyro_mag_mean_dps=("gyro_magnitude_dps", "mean"),
            hx_filt_mean_counts=("hx711_filtered_counts", "mean"),
            hx_filt_std_counts=("hx711_filtered_counts", "std"),
            total_vehicle_crossings=("vehicle_crossing_delta", "sum"),
        )
        .reset_index()
    )
    return run_summary, condition_summary


def generate_comparison_plots(df: pd.DataFrame, output_dir: Path) -> List[Path]:
    """Generate comparative condition boxplots/bars and time-series profiles."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_plots: List[Path] = []

    is_synthetic = "synthetic" in df["data_source"].unique()
    source_tag = "SYNTHETIC DEMO DATA" if is_synthetic else "EXPERIMENTAL PROTOTYPE DATA"

    conditions = [c for c in ("baseline", "static_load", "vehicle_crossing") if c in df["condition"].unique()]
    palette = {"baseline": "#2b5c8f", "static_load": "#d95f02", "vehicle_crossing": "#1b9e77"}

    # Plot 1: 4-Panel Condition Comparison
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        f"Structural Health IoT Analytics — Condition Comparison ({source_tag})",
        fontsize=14,
        fontweight="bold",
    )

    # Panel A: Vibration RMS by Condition
    ax = axes[0, 0]
    data_rms = [df.loc[df["condition"] == c, "vibration_rms_g"].values for c in conditions]
    bp1 = ax.boxplot(data_rms, tick_labels=conditions, patch_artist=True)
    for patch, c in zip(bp1["boxes"], conditions):
        patch.set_facecolor(palette.get(c, "#888888"))
        patch.set_alpha(0.75)
    ax.set_title("A. Dynamic Vibration RMS by Condition")
    ax.set_ylabel("Vibration RMS (g)")
    ax.grid(True, linestyle="--", alpha=0.4)

    # Panel B: Peak Vibration by Condition
    ax = axes[0, 1]
    data_peak = [df.loc[df["condition"] == c, "vibration_peak_g"].values for c in conditions]
    bp2 = ax.boxplot(data_peak, tick_labels=conditions, patch_artist=True)
    for patch, c in zip(bp2["boxes"], conditions):
        patch.set_facecolor(palette.get(c, "#888888"))
        patch.set_alpha(0.75)
    ax.set_title("B. Peak Dynamic Vibration by Condition")
    ax.set_ylabel("Peak Vibration (g)")
    ax.grid(True, linestyle="--", alpha=0.4)

    # Panel C: HX711 Tare-Relative Filtered Counts (Support Reaction)
    ax = axes[1, 0]
    data_hx = [df.loc[df["condition"] == c, "hx711_filtered_counts"].values for c in conditions]
    bp3 = ax.boxplot(data_hx, tick_labels=conditions, patch_artist=True)
    for patch, c in zip(bp3["boxes"], conditions):
        patch.set_facecolor(palette.get(c, "#888888"))
        patch.set_alpha(0.75)
    ax.set_title("C. Support Reaction — HX711 Filtered Counts (Tare-Relative)")
    ax.set_ylabel("HX711 Filtered Counts")
    ax.grid(True, linestyle="--", alpha=0.4)

    # Panel D: Vibration RMS vs HX711 Filtered Counts Scatter
    ax = axes[1, 1]
    for c in conditions:
        sub = df[df["condition"] == c]
        ax.scatter(
            sub["hx711_filtered_counts"],
            sub["vibration_rms_g"],
            label=c,
            color=palette.get(c, "#333333"),
            alpha=0.75,
            edgecolors="k",
            s=40,
        )
    ax.set_title("D. Feature Space: Support Reaction Counts vs Vibration RMS")
    ax.set_xlabel("HX711 Filtered Counts (Tare-Relative)")
    ax.set_ylabel("Vibration RMS (g)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    comp_path = output_dir / "condition_comparison.png"
    fig.savefig(comp_path, dpi=150)
    plt.close(fig)
    saved_plots.append(comp_path)

    # Plot 2: Representative Trial Time-Series Profiles
    fig2, axes2 = plt.subplots(3, 1, figsize=(12, 8), sharex=False)
    fig2.suptitle(
        f"Representative Trial Time-Series Profiles ({source_tag})",
        fontsize=13,
        fontweight="bold",
    )
    for idx, c in enumerate(conditions):
        first_run = df.loc[df["condition"] == c, "run_id"].iloc[0]
        run_df = df[df["run_id"] == first_run].reset_index(drop=True)
        t_sec = np.arange(len(run_df))
        ax_ts = axes2[idx]
        ax_ts.plot(
            t_sec,
            run_df["vibration_rms_g"],
            color=palette.get(c, "#2b5c8f"),
            linewidth=2,
            marker="o",
            markersize=4,
            label="Vibration RMS (g)",
        )
        ax_ts.plot(
            t_sec,
            run_df["vibration_peak_g"],
            color="#e7298a",
            linewidth=1.5,
            linestyle="--",
            label="Vibration Peak (g)",
        )
        ax_ts.set_title(f"Condition: {c} (Run: {first_run})")
        ax_ts.set_ylabel("Accel (g)")
        ax_ts.legend(loc="upper right")
        ax_ts.grid(True, linestyle="--", alpha=0.4)
    axes2[-1].set_xlabel("Sample Index within Trial (~1 Hz reporting window)")
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    ts_path = output_dir / "trial_timeseries.png"
    fig2.savefig(ts_path, dpi=150)
    plt.close(fig2)
    saved_plots.append(ts_path)

    return saved_plots


def run_analysis(data_path: Path, results_dir: Path) -> dict:
    """Execute the complete exploratory analysis pipeline and export CSV summaries + plots."""
    raw_df = load_csv_files(data_path)
    df = engineer_features(raw_df)
    run_summary, condition_summary = compute_summaries(df)

    results_dir.mkdir(parents=True, exist_ok=True)
    run_csv = results_dir / "trial_summary.csv"
    cond_csv = results_dir / "condition_summary.csv"
    run_summary.to_csv(run_csv, index=False)
    condition_summary.to_csv(cond_csv, index=False)

    plots = generate_comparison_plots(df, results_dir)

    print("============================================================")
    print(" STRUCTURAL HEALTH IoT — ANALYTICS SUMMARY")
    print("============================================================")
    print(f"  Input Dataset      : {data_path}")
    print(f"  Data Sources       : {sorted(df['data_source'].unique().tolist())}")
    print(f"  Total Valid Rows   : {len(df)} across {df['run_id'].nunique()} runs")
    print("\nCondition Aggregate Summary:")
    print(condition_summary.to_string(index=False))
    print(f"\nSaved summaries and plots to: {results_dir}")
    for p in [run_csv, cond_csv] + plots:
        print(f"  - {p}")
    print("============================================================")

    return {
        "rows": len(df),
        "runs": int(df["run_id"].nunique()),
        "run_summary_path": str(run_csv),
        "condition_summary_path": str(cond_csv),
        "plot_paths": [str(p) for p in plots],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run comparative data analytics on bridge IoT trials.")
    parser.add_argument(
        "--data",
        default=str(REPO_ROOT / "data" / "sample" / "synthetic_trials.csv"),
        help="Path to CSV file or directory (e.g. data/experimental or data/sample/synthetic_trials.csv)",
    )
    parser.add_argument(
        "--results-dir",
        default=str(ANALYTICS_DIR / "results"),
        help="Output directory for summary CSVs and plots",
    )
    args = parser.parse_args(argv)
    run_analysis(Path(args.data), Path(args.results_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
