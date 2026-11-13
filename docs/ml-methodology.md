# Machine Learning Methodology & Scope (`docs/ml-methodology.md`)

## 1. Objective & Engineering Scope

In this project, Machine Learning is an **interpretable analytical layer** on top of the end-to-end IoT pipeline (**ESP32 → MQTT → InfluxDB → Grafana**).

We use a shallow `DecisionTreeClassifier` (`max_depth=4`, `min_samples_leaf=2`, `random_state=42`) from `scikit-learn` to classify experimentally observed operating conditions on the tabletop bridge prototype:

1. `baseline` — Bridge deck unloaded at rest.
2. `static_load` — Bridge deck carrying a stationary applied mass at a marked position.
3. `vehicle_crossing` — Small toy car traversing the bridge deck through the two IR obstacle gates.

### What the Model Predicts vs What It Does NOT Predict

| What the Classifier Predicts | What the Classifier Does NOT Predict |
|---|---|
| Which of the 3 controlled experimental regimes (`baseline`, `static_load`, `vehicle_crossing`) a given telemetry window belongs to. | Real-world bridge failure, fatigue crack propagation, or structural collapse. |
| How vibration features (`vibration_rms_g`, `vibration_peak_g`), support-reaction counts (`hx711_filtered_counts`), and IR crossing events jointly separate static loading from dynamic vehicle passes. | Engineering safety certification or civil structural health ratings. |
| Human-readable threshold splits (`export_text`) that can be inspected and explained during a viva. | Direct deck displacement (`deflection_mm`), since the VL53L0X ToF sensor was dropped. |

---

## 2. Feature Engineering (`analytics-ml/preprocess.py`)

Each telemetry sample is mapped to an 8-dimensional feature vector derived strictly from the three active sensor groups:

| Feature Name | Sensor Source | Mathematical / Physical Definition |
|---|---|---|
| `vibration_rms_g` | IMU (GY-521) | $\sqrt{\frac{1}{N}\sum_{k=1}^{N} \|\mathbf{a}_k - \mathbf{g}_{\text{LPF}}\|^2}$ over the 100 Hz window ($g$) |
| `vibration_peak_g` | IMU (GY-521) | $\max_k \|\mathbf{a}_k - \mathbf{g}_{\text{LPF}}\|$ over the 100 Hz window ($g$) |
| `accel_dynamic_g` | IMU (GY-521) | $\left|\sqrt{a_x^2 + a_y^2 + a_z^2} - 1.0\right|$ ($g$) |
| `gyro_magnitude_dps` | IMU (GY-521) | $\sqrt{g_x^2 + g_y^2 + g_z^2}$ ($^\circ/\text{s}$) |
| `hx711_filtered_counts` | Load Cell + HX711 | Tare-relative EMA-filtered ADC counts at the instrumented support |
| `ir_blocked_sensors` | Dual IR Gates | Number of IR sensors currently blocked ($\mathbb{I}[\text{ir1}=0] + \mathbb{I}[\text{ir2}=0]$) |
| `ir_event_rate` | Dual IR Gates | Rolling 5-sample sum of new obstacle transitions within the same `run_id` |
| `vehicle_crossing_delta` | Dual IR Gates | Rolling 5-sample sum of completed vehicle crossings within the same `run_id` |

> **Why `hx711_filtered_counts` is used instead of requiring `load_grams`:**
> Using tare-relative filtered counts allows the classifier to work both before and after known-mass calibration, while avoiding any silent fabrication of gram values.

---

## 3. Preventing Data Leakage: Group-Aware Splitting by `run_id`

Time-series sensor readings captured at 1 Hz within a single 30-second trial (`run_id`) are strongly autocorrelated. A naive random row-wise `train_test_split` puts adjacent seconds from the exact same physical trial into both the training and test sets, artificially inflating test accuracy.

To prevent this leakage, `analytics-ml/train_model.py` implements **stratified group splitting by `run_id`** (`split_by_independent_runs()`):

- Every row from a given `run_id` goes **entirely** into either the training set or the held-out test set—never both.
- For each condition class (`baseline`, `static_load`, `vehicle_crossing`), 25% of the independent runs (minimum 1 full run per class) are held out for testing.

---

## 4. Statistical Readiness Check & Honest Reporting

Before training, `assess_ml_readiness()` checks whether the supplied dataset meets three minimum statistical criteria:
1. At least **2 condition classes** present (all 3 recommended).
2. At least **2 independent runs (`run_id`) per class** (4+ per class recommended).
3. At least **20 validated rows** after cleaning.

If a dataset fails any of these checks (for example, if only one quick test run has been recorded so far), `train_model.py` **refuses to fabricate a train/test accuracy score**, outputs `"status": "INSUFFICIENT_DATA_FOR_VALID_EVALUATION"` in `evaluation_report.json`, and prints the exact trial requirements needed.
