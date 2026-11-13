# Analytics & Interpretable Machine Learning (`analytics-ml/`)

## Scope & Role in the IoT Architecture

The end-to-end IoT pipeline (**ESP32 → Wi-Fi → Mosquitto MQTT → Python Ingestor → InfluxDB 2.x → Grafana**) is the primary system deliverable. This folder implements the **Analyze** stage on top of collected time-series data using **NumPy, Pandas, Matplotlib, and Scikit-learn**.

> **Important Scope Discipline:**
> - The VL53L0X ToF displacement sensor (`deflection_mm`) has been dropped from the hardware and is completely excluded from all schemas, plots, and ML features.
> - The `DecisionTreeClassifier` classifies experimentally observed operating conditions (`baseline`, `static_load`, `vehicle_crossing`) on the tabletop bridge prototype. It **does not** predict real-world bridge failure, structural safety, or engineering certification.

---

## Scripts in `analytics-ml/`

| Script | Purpose |
|---|---|
| `preprocess.py` | Schema validation, legacy column stripping, timestamp alignment, per-run feature engineering (`accel_dynamic_g`, `gyro_magnitude_dps`, `ir_blocked_sensors`, `ir_event_rate`, `vehicle_crossing_delta`), and statistical readiness checks. |
| `analyze_trials.py` | Produces per-run (`trial_summary.csv`) and per-condition (`condition_summary.csv`) statistics and generates comparative plots (`condition_comparison.png`, `trial_timeseries.png`) in `analytics-ml/results/`. |
| `train_model.py` | Performs **group-aware train/test splitting by `run_id`** (preventing row-wise data leakage from adjacent samples of the same trial), trains a fixed-seed `DecisionTreeClassifier(random_state=42)`, and outputs accuracy, precision, recall, F1-score, confusion matrix, feature importances, and human-readable tree rules. |
| `predict.py` | Loads `analytics-ml/results/decision_tree_model.joblib` and classifies new single observations (via CLI flags or JSON) or batch CSV files. |

---

## Feature Vector (8 Interpretable Features)

1. `vibration_rms_g` — Windowed RMS of dynamic acceleration after gravity removal ($g$).
2. `vibration_peak_g` — Peak dynamic acceleration magnitude in the reporting window ($g$).
3. `accel_dynamic_g` — Instantaneous deviation of 3-axis acceleration norm from $1\,g$.
4. `gyro_magnitude_dps` — 3-axis angular velocity magnitude $\sqrt{g_x^2 + g_y^2 + g_z^2}$ ($^\circ/\text{s}$).
5. `hx711_filtered_counts` — Tare-relative EMA-filtered counts from the HX711 at the instrumented support.
6. `ir_blocked_sensors` — Number of IR gates currently blocked ($0$, $1$, or $2$).
7. `ir_event_rate` — Rolling within-run IR transition count over 5 samples.
8. `vehicle_crossing_delta` — Rolling within-run vehicle crossings over 5 samples.

---

## Commands

```powershell
# 1. Generate/refresh the synthetic demonstration dataset (labelled data_source=synthetic)
python scripts/generate_sample_data.py

# 2. Run comparative analytics and generate plots on the synthetic demo dataset
python analytics-ml/analyze_trials.py --data data/sample/synthetic_trials.csv

# 3. Train and evaluate the Decision Tree classifier (group-split by run_id)
python analytics-ml/train_model.py --data data/sample/synthetic_trials.csv

# 4. Run a prediction on a single observation
python analytics-ml/predict.py --vibration-rms-g 0.074 --vibration-peak-g 0.210 --hx711-filtered-counts 4200 --ir1-state 0 --vehicle-crossing-delta 1

# 5. Once real experimental CSVs are recorded in data/experimental/, run on real data:
python analytics-ml/analyze_trials.py --data data/experimental
python analytics-ml/train_model.py --data data/experimental
```
