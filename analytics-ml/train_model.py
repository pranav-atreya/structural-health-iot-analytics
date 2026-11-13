"""Interpretable Decision Tree Classifier Training & Group-Aware Evaluation.

Classifies experimentally observed operating conditions on the tabletop bridge:
  - baseline
  - static_load
  - vehicle_crossing

CRITICAL METHODOLOGY & SCOPE NOTES:
  1. Group-Aware Splitting: Rows from the same experimental run (`run_id`) are NEVER
     split across training and testing sets. Independent runs are held out per class
     to prevent temporal autocorrelation data leakage.
  2. Statistical Honesty: If the supplied dataset contains only 1 class or fewer than
     2 independent runs per class, this script does NOT fabricate an evaluation score;
     it clearly reports that statistically meaningful evaluation is not yet possible
     and lists the exact trial requirements.
  3. Engineering Scope: This classifier distinguishes the experimental operating
     conditions represented in the dataset. It does NOT predict real-world bridge
     failure, structural safety, or engineering certification.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.tree import DecisionTreeClassifier, export_text

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = Path(__file__).resolve().parent
for p in (str(REPO_ROOT), str(ANALYTICS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from preprocess import (  # noqa: E402
    ML_FEATURE_COLUMNS,
    assess_ml_readiness,
    engineer_features,
    load_csv_files,
)

RANDOM_SEED = 42


def split_by_independent_runs(
    df: pd.DataFrame,
    test_run_fraction: float = 0.25,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str], List[str]]:
    """Split dataset by `run_id` stratified across `condition` classes so no run leaks across sets."""
    rng = np.random.default_rng(seed)
    train_runs: List[str] = []
    test_runs: List[str] = []

    for cond in sorted(df["condition"].unique()):
        cond_runs = sorted(df.loc[df["condition"] == cond, "run_id"].unique().tolist())
        shuffled = list(cond_runs)
        rng.shuffle(shuffled)
        n_test = max(1, int(round(len(shuffled) * test_run_fraction)))
        if len(shuffled) - n_test < 1:
            n_test = 1
        test_runs.extend(shuffled[:n_test])
        train_runs.extend(shuffled[n_test:])

    train_df = df[df["run_id"].isin(train_runs)].copy().reset_index(drop=True)
    test_df = df[df["run_id"].isin(test_runs)].copy().reset_index(drop=True)
    return train_df, test_df, sorted(train_runs), sorted(test_runs)


def save_evaluation_plots(
    cm: np.ndarray,
    labels: List[str],
    feature_names: List[str],
    importances: np.ndarray,
    output_dir: Path,
    source_tag: str,
) -> Tuple[Path, Path]:
    """Save Confusion Matrix and Feature Importance plots."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Confusion Matrix
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    fig.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(len(labels)),
        yticks=np.arange(len(labels)),
        xticklabels=labels,
        yticklabels=labels,
        ylabel="True Experimental Condition",
        xlabel="Predicted Operating Condition",
        title=f"Decision Tree Confusion Matrix ({source_tag})",
    )
    thresh = cm.max() / 2.0 if cm.size > 0 else 0.5
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                format(cm[i, j], "d"),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontweight="bold",
            )
    plt.tight_layout()
    cm_path = output_dir / "confusion_matrix.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)

    # 2. Feature Importance
    order = np.argsort(importances)
    fig2, ax2 = plt.subplots(figsize=(8, 4.8))
    ax2.barh(
        [feature_names[i] for i in order],
        importances[order],
        color="#2b5c8f",
        edgecolor="black",
    )
    ax2.set_xlabel("Gini Feature Importance")
    ax2.set_title(f"Decision Tree Feature Importance ({source_tag})")
    ax2.set_xlim(0, max(0.05, float(importances.max()) * 1.15))
    ax2.grid(True, axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()
    fi_path = output_dir / "feature_importance.png"
    fig2.savefig(fi_path, dpi=150)
    plt.close(fig2)

    return cm_path, fi_path


def train_and_evaluate(
    data_path: Path,
    results_dir: Path,
    max_depth: int = 4,
    seed: int = RANDOM_SEED,
) -> Dict[str, Any]:
    """Run the full preprocessing, readiness check, Decision Tree training, and evaluation."""
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_df = load_csv_files(data_path)
    df = engineer_features(raw_df)
    readiness = assess_ml_readiness(df, min_runs_per_class=2)

    if not readiness.is_ready_for_group_ml:
        report = {
            "status": "INSUFFICIENT_DATA_FOR_VALID_EVALUATION",
            "statistically_meaningful": False,
            "data_path": str(data_path),
            "data_sources": readiness.data_sources,
            "total_samples": readiness.total_samples,
            "classes_present": readiness.classes_present,
            "runs_per_class": readiness.runs_per_class,
            "reasons": readiness.reasons,
            "requirements_for_valid_training": {
                "min_classes": 2,
                "recommended_classes": ["baseline", "static_load", "vehicle_crossing"],
                "min_independent_runs_per_class": 2,
                "recommended_runs_per_class": 4,
                "min_total_samples": 20,
            },
        }
        report_path = results_dir / "evaluation_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print("============================================================")
        print(" ML READINESS CHECK — INSUFFICIENT INDEPENDENT TRIALS")
        print("============================================================")
        print("Proper model evaluation is NOT YET STATISTICALLY MEANINGFUL:")
        for reason in readiness.reasons:
            print(f"  - {reason}")
        print("\nRequirements for valid group-aware evaluation:")
        print("  - At least 2 (preferably all 3) condition classes: baseline, static_load, vehicle_crossing")
        print("  - At least 2 independent trial runs (unique run_id) per condition class")
        print("  - At least 20 total validated samples")
        print("============================================================")
        return report

    train_df, test_df, train_runs, test_runs = split_by_independent_runs(df, seed=seed)

    X_train = train_df[ML_FEATURE_COLUMNS]
    y_train = train_df["condition"]
    X_test = test_df[ML_FEATURE_COLUMNS]
    y_test = test_df["condition"]

    clf = DecisionTreeClassifier(
        criterion="gini",
        max_depth=max_depth,
        min_samples_leaf=2,
        random_state=seed,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    labels = sorted(df["condition"].unique().tolist())

    acc = float(accuracy_score(y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cls_report_str = classification_report(y_test, y_pred, labels=labels, zero_division=0)
    cls_report_dict = classification_report(
        y_test, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    tree_rules = export_text(clf, feature_names=ML_FEATURE_COLUMNS)

    feature_importance_map = {
        feat: round(float(imp), 4)
        for feat, imp in zip(ML_FEATURE_COLUMNS, clf.feature_importances_)
    }

    is_synthetic = "synthetic" in readiness.data_sources
    source_tag = "SYNTHETIC DEMO DATA" if is_synthetic else "EXPERIMENTAL PROTOTYPE DATA"

    cm_path, fi_path = save_evaluation_plots(
        cm=cm,
        labels=labels,
        feature_names=ML_FEATURE_COLUMNS,
        importances=clf.feature_importances_,
        output_dir=results_dir,
        source_tag=source_tag,
    )

    model_bundle = {
        "model": clf,
        "feature_columns": ML_FEATURE_COLUMNS,
        "classes": list(clf.classes_),
        "data_sources": readiness.data_sources,
        "is_synthetic_model": is_synthetic,
        "random_seed": seed,
        "train_runs": train_runs,
        "test_runs": test_runs,
    }
    model_path = results_dir / "decision_tree_model.joblib"
    joblib.dump(model_bundle, model_path)

    report = {
        "status": "SUCCESS",
        "statistically_meaningful": True,
        "is_synthetic_demonstration": is_synthetic,
        "scope_statement": (
            "Classifies tabletop prototype operating conditions (baseline, static_load, "
            "vehicle_crossing). Does NOT predict bridge failure or real-world structural safety."
        ),
        "data_path": str(data_path),
        "data_sources": readiness.data_sources,
        "random_seed": seed,
        "feature_columns": ML_FEATURE_COLUMNS,
        "classes": labels,
        "train_runs": train_runs,
        "test_runs": test_runs,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "metrics": {
            "accuracy": round(acc, 4),
            "macro_precision": round(float(prec), 4),
            "macro_recall": round(float(rec), 4),
            "macro_f1": round(float(f1), 4),
        },
        "confusion_matrix": {
            "labels": labels,
            "matrix": cm.tolist(),
        },
        "feature_importances": feature_importance_map,
        "classification_report": cls_report_dict,
        "decision_tree_rules": tree_rules,
        "artifacts": {
            "model_joblib": str(model_path),
            "confusion_matrix_plot": str(cm_path),
            "feature_importance_plot": str(fi_path),
        },
    }

    report_path = results_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("============================================================")
    print(f" DECISION TREE CLASSIFIER EVALUATION ({source_tag})")
    print("============================================================")
    print(f"  Data Sources     : {readiness.data_sources}")
    print(f"  Train Runs ({len(train_runs):02d}) : {train_runs} ({len(train_df)} rows)")
    print(f"  Test Runs  ({len(test_runs):02d}) : {test_runs} ({len(test_df)} rows)")
    print(f"  Accuracy         : {acc:.4f}")
    print(f"  Macro Precision  : {prec:.4f}")
    print(f"  Macro Recall     : {rec:.4f}")
    print(f"  Macro F1-Score   : {f1:.4f}")
    print("\nClassification Report:")
    print(cls_report_str)
    print("Feature Importances:")
    for feat, imp in sorted(feature_importance_map.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {feat:26s}: {imp:.4f}")
    print("\nDecision Tree Rules:")
    print(tree_rules)
    print(f"Saved model artifact to: {model_path}")
    print("============================================================")

    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train and evaluate an interpretable DecisionTreeClassifier on bridge IoT trials."
    )
    parser.add_argument(
        "--data",
        default=str(REPO_ROOT / "data" / "sample" / "synthetic_trials.csv"),
        help="Path to trial CSV file or directory (default: data/sample/synthetic_trials.csv)",
    )
    parser.add_argument(
        "--results-dir",
        default=str(ANALYTICS_DIR / "results"),
        help="Directory to write model artifact, plots, and evaluation JSON",
    )
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum depth of Decision Tree")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Fixed random seed")
    args = parser.parse_args(argv)

    train_and_evaluate(
        data_path=Path(args.data),
        results_dir=Path(args.results_dir),
        max_depth=args.max_depth,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
