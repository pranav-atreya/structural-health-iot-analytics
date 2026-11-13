"""Operating Condition Prediction CLI — Structural Health IoT Analytics.

Uses the trained DecisionTreeClassifier (`analytics-ml/results/decision_tree_model.joblib`)
to predict the experimental operating condition (`baseline`, `static_load`, or
`vehicle_crossing`) for a single telemetry sample, JSON payload, or CSV file.

IMPORTANT SCOPE NOTE:
  This model classifies which experimental operating regime an observation resembles
  based on the training dataset. It does NOT predict structural failure or real-world
  bridge safety.

Usage examples:
  # Predict from CLI feature flags:
  python analytics-ml/predict.py --vibration-rms-g 0.011 --vibration-peak-g 0.028 --hx711-filtered-counts 12
  python analytics-ml/predict.py --vibration-rms-g 0.014 --vibration-peak-g 0.032 --hx711-filtered-counts 13200
  python analytics-ml/predict.py --vibration-rms-g 0.075 --vibration-peak-g 0.210 --hx711-filtered-counts 4100 --ir1-state 0 --vehicle-crossing-delta 1

  # Predict on an entire CSV file:
  python analytics-ml/predict.py --csv data/sample/sample-format.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = Path(__file__).resolve().parent
for p in (str(REPO_ROOT), str(ANALYTICS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from preprocess import (  # noqa: E402
    ML_FEATURE_COLUMNS,
    engineer_features,
    extract_single_sample_features,
    load_csv_files,
)


def predict_single_observation(
    model_path: Path,
    observation: Dict[str, Any],
) -> Dict[str, Any]:
    """Load saved DecisionTreeClassifier bundle and predict operating condition for one sample."""
    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model artifact not found at {model_path}. Run `python analytics-ml/train_model.py` first."
        )

    bundle = joblib.load(model_path)
    clf = bundle["model"]
    classes = list(clf.classes_)

    X = extract_single_sample_features(observation)
    pred_label = str(clf.predict(X)[0])
    probs = clf.predict_proba(X)[0]
    prob_map = {cls: round(float(p), 4) for cls, p in zip(classes, probs)}

    return {
        "predicted_condition": pred_label,
        "class_probabilities": prob_map,
        "features_used": X.iloc[0].to_dict(),
        "model_trained_on_sources": bundle.get("data_sources", ["unknown"]),
        "is_synthetic_model": bool(bundle.get("is_synthetic_model", False)),
        "scope_disclaimer": (
            "Predicts tabletop prototype experimental condition only; "
            "not a structural failure or safety certification."
        ),
    }


def predict_csv_file(model_path: Path, csv_path: Path) -> pd.DataFrame:
    """Predict operating conditions for all rows in a CSV file."""
    bundle = joblib.load(model_path)
    clf = bundle["model"]

    raw_df = load_csv_files(csv_path)
    df = engineer_features(raw_df)
    X = df[ML_FEATURE_COLUMNS]
    df["predicted_condition"] = clf.predict(X)
    return df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predict tabletop bridge operating condition using the trained Decision Tree."
    )
    parser.add_argument(
        "--model",
        default=str(ANALYTICS_DIR / "results" / "decision_tree_model.joblib"),
        help="Path to trained .joblib model bundle",
    )
    parser.add_argument("--csv", default=None, help="Optional CSV file path to batch-predict")
    parser.add_argument("--json", default=None, help="Optional raw JSON telemetry string to classify")
    parser.add_argument("--vibration-rms-g", type=float, default=0.012)
    parser.add_argument("--vibration-peak-g", type=float, default=0.030)
    parser.add_argument("--ax-g", type=float, default=0.005)
    parser.add_argument("--ay-g", type=float, default=-0.004)
    parser.add_argument("--az-g", type=float, default=0.998)
    parser.add_argument("--gx-dps", type=float, default=0.10)
    parser.add_argument("--gy-dps", type=float, default=-0.08)
    parser.add_argument("--gz-dps", type=float, default=0.05)
    parser.add_argument("--hx711-filtered-counts", type=float, default=0.0)
    parser.add_argument("--ir1-state", type=int, default=1)
    parser.add_argument("--ir2-state", type=int, default=1)
    parser.add_argument("--ir-event-rate", type=float, default=0.0)
    parser.add_argument("--vehicle-crossing-delta", type=float, default=0.0)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    model_path = Path(args.model)

    if args.csv:
        df_out = predict_csv_file(model_path, Path(args.csv))
        cols = ["run_id", "condition", "predicted_condition", "vibration_rms_g", "hx711_filtered_counts", "vehicle_count"]
        print(df_out[cols].to_string(index=False))
        return 0

    if args.json:
        obs = json.loads(args.json)
    else:
        obs = {
            "vibration_rms_g": args.vibration_rms_g,
            "vibration_peak_g": args.vibration_peak_g,
            "ax_g": args.ax_g,
            "ay_g": args.ay_g,
            "az_g": args.az_g,
            "gx_dps": args.gx_dps,
            "gy_dps": args.gy_dps,
            "gz_dps": args.gz_dps,
            "hx711_filtered_counts": args.hx711_filtered_counts,
            "ir1_state": args.ir1_state,
            "ir2_state": args.ir2_state,
            "ir_event_rate": args.ir_event_rate,
            "vehicle_crossing_delta": args.vehicle_crossing_delta,
        }

    result = predict_single_observation(model_path, obs)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
