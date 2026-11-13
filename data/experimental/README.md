# Experimental Data Directory (`data/experimental/`)

Store genuine experimental trial CSV files captured from the physical tabletop bridge prototype here.

## How to Record a Trial

Run `scripts/record_trial.py` while the ESP32 is streaming over MQTT (or USB Serial):

```powershell
# 1. Unloaded baseline trial (30 seconds)
python scripts/record_trial.py --run-id EXP_01 --condition baseline --duration 30 --notes "Unloaded bridge deck at rest"

# 2. Static load trial with known mass (e.g., 100 g at mid-span)
python scripts/record_trial.py --run-id EXP_02 --condition static_load --applied-mass-g 100 --load-position "mid-span" --duration 30 --notes "100g mass at mid-span"

# 3. Dynamic toy-vehicle crossing trial
python scripts/record_trial.py --run-id EXP_03 --condition vehicle_crossing --load-position "1_to_2" --duration 45 --notes "Repeated toy car crossings 1->2"
```

## Data Integrity Rules

1. **Never place synthetic or simulated data in `data/experimental/`.** Synthetic demonstration files belong strictly in `data/sample/` with `data_source = "synthetic"`.
2. **`record_trial.py` never overwrites existing CSV files.** If a `run_id` already exists, a UTC timestamp suffix is appended automatically.
3. **Never commit Wi-Fi passwords, MQTT passwords, or API tokens.**
