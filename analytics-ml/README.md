# Analytics and ML

## Scope

The IoT pipeline is the primary project. Analytics and a small ML model are part of the Analyze stage. Keep the model simple and interpretable.

## Planned workflow

1. Obtain exported ThingSpeak CSV data.
2. Keep a separate experiment log containing run ID, condition label, applied mass, placement and trial notes.
3. Clean and align timestamps.
4. Compute/verify features: vibration RMS, peak vibration, deflection, support reaction and crossing count.
5. Visualize static-load and vehicle-crossing responses.
6. Train a small Decision Tree classifier to distinguish experimentally labelled conditions.
7. Evaluate on held-out runs/trials and report accuracy plus a confusion matrix.

## Suggested classes

Only use classes that can be consistently produced and labelled in the actual experiment, for example:
- baseline
- static_load
- vehicle_crossing

Add a repeated_crossing class only if enough independent runs are collected.

## Data integrity

- Synthetic/sample records are only for software development and must be labelled as synthetic.
- Do not invent experimental values.
- Do not randomly split adjacent rows from the same experiment between training and test sets; split by run/trial where possible.
- Do not describe the classifier as predicting bridge failure or real-world structural safety.
