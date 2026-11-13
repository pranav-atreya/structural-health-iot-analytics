"""Load-Cell Calibration Utility — Sharvi 1 kg Bar Load Cell + HX711.

Provides a reproducible two-point or multi-sample calibration procedure using a
known reference mass (in grams) to determine `HX711_CALIBRATION_FACTOR` (counts/g).

IMPORTANT PHYSICAL NOTE:
  - The load cell is mounted under ONE bridge support. Its calibrated output represents
    the **support reaction at the instrumented support**, NOT the total load on the bridge.
  - A preliminary observation with an ~50 g bottle produced ~12,830 counts (~256.6 counts/g),
    which is ONLY an unvalidated preliminary observation and is NOT hardcoded as a calibration.

Usage examples:
  # Compute calibration factor from observed unloaded and loaded raw/net counts:
  python scripts/calibrate_load_cell.py --known-mass-g 100.0 --tare-counts -381709 --loaded-counts -356049

  # Or pass net counts directly:
  python scripts/calibrate_load_cell.py --known-mass-g 50.0 --net-counts 12830
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import sys
from typing import List, Optional, Sequence


@dataclass
class CalibrationResult:
    """Result of a known-mass load cell calibration calculation."""

    known_mass_g: float
    tare_counts: float
    loaded_counts: float
    net_counts: float
    calibration_factor_counts_per_g: float
    std_net_counts: float


def compute_calibration_factor(
    known_mass_g: float,
    net_counts_samples: Sequence[float],
    tare_counts: float = 0.0,
) -> CalibrationResult:
    """Compute the HX711 calibration factor (counts per gram) from known mass and net counts."""
    if known_mass_g <= 0.0 or not math.isfinite(known_mass_g):
        raise ValueError("known_mass_g must be a positive finite number of grams")
    if not net_counts_samples:
        raise ValueError("At least one net_counts reading is required")

    clean_samples = [float(x) for x in net_counts_samples]
    if any(not math.isfinite(x) for x in clean_samples):
        raise ValueError("All count readings must be finite numbers")

    mean_net = sum(clean_samples) / len(clean_samples)
    if abs(mean_net) < 10.0:
        raise ValueError(
            f"Mean net counts ({mean_net:.2f}) is too small (< 10 counts). "
            "Verify that the reference mass is placed on the instrumented support."
        )

    if len(clean_samples) > 1:
        variance = sum((x - mean_net) ** 2 for x in clean_samples) / (len(clean_samples) - 1)
        std_net = math.sqrt(variance)
    else:
        std_net = 0.0

    factor = mean_net / known_mass_g
    return CalibrationResult(
        known_mass_g=known_mass_g,
        tare_counts=float(tare_counts),
        loaded_counts=float(tare_counts) + mean_net,
        net_counts=mean_net,
        calibration_factor_counts_per_g=factor,
        std_net_counts=std_net,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute HX711 load-cell calibration factor (counts/g) from a known reference mass."
    )
    parser.add_argument(
        "--known-mass-g",
        type=float,
        required=True,
        help="Known reference mass in grams placed directly over the instrumented support",
    )
    parser.add_argument(
        "--tare-counts",
        type=float,
        default=0.0,
        help="Unloaded raw HX711 counts (zero offset)",
    )
    parser.add_argument(
        "--loaded-counts",
        type=float,
        nargs="+",
        default=None,
        help="One or more raw HX711 count readings with the reference mass applied",
    )
    parser.add_argument(
        "--net-counts",
        type=float,
        nargs="+",
        default=None,
        help="One or more tare-relative net count readings (hx_net / hx_filtered)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.net_counts is not None:
        net_samples = args.net_counts
    elif args.loaded_counts is not None:
        net_samples = [raw - args.tare_counts for raw in args.loaded_counts]
    else:
        parser.error("Provide either --net-counts or --loaded-counts (with --tare-counts)")
        return 2

    result = compute_calibration_factor(
        known_mass_g=args.known_mass_g,
        net_counts_samples=net_samples,
        tare_counts=args.tare_counts,
    )

    print("============================================================")
    print(" SHARVI 1 KG LOAD CELL + HX711 CALIBRATION REPORT")
    print("============================================================")
    print(f"  Reference Mass         : {result.known_mass_g:.2f} g")
    print(f"  Unloaded Tare Offset   : {result.tare_counts:.1f} counts")
    print(f"  Mean Net Counts        : {result.net_counts:.2f} counts (std={result.std_net_counts:.2f})")
    print(f"  Calibration Factor     : {result.calibration_factor_counts_per_g:.4f} counts/g")
    print("------------------------------------------------------------")
    print("  Physical Interpretation:")
    print("    The calibrated value measures the reaction at the single")
    print("    instrumented support, NOT the total bridge deck load.")
    print("------------------------------------------------------------")
    print("  To enable calibrated support reaction (`load_grams`) in ESP32 firmware,")
    print("  update `firmware/structural_health_monitor/secrets.h`:")
    print(f"\n    #define HX711_CALIBRATION_FACTOR  {result.calibration_factor_counts_per_g:.4f}f\n")
    print("  Or send via Serial Monitor (115200 baud) while mass is applied:")
    print(f"    C {result.known_mass_g:.2f}")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
