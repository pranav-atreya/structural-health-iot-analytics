# Hardware Bill of Materials

## Existing components

- 1 × ESP32 DevKit (available)
- 1 × MPU6050 / GY-521 IMU module (available)
- 1–2 × toy cars (at least one available)

## Required sensing/electronics components

- 1 × VL53L0X I²C ToF distance sensor breakout
- 1 × four-wire bar-type load cell (suggested 1 kg nominal capacity; select based on mechanical design and expected loads)
- 1 × HX711 load-cell ADC/amplifier module
- 1 × 940 nm IR LED transmitter
- 1 × matching 940 nm phototransistor receiver
- 1 × 220 Ω resistor for IR LED current limiting (verify LED datasheet/current)
- 1 × 10 kΩ resistor for receiver pull-up (adjust circuit based on receiver topology)

## Mechanical materials

- 1 × flexible metal ruler/strip for bridge deck (approximately 25–30 cm)
- 1 × rigid MDF/plywood base (approximately 40 × 15 cm)
- 2 × support blocks
- Load-cell mounting bracket and plate compatible with the actual load-cell model
- ToF mounting bracket
- Screws, nuts and washers as required

## Reusable accessories (verify before purchase)

- Breadboard
- Male-to-male and male-to-female jumper wires
- USB data cable suitable for the ESP32
- Multimeter
- Known/calibrated masses or a kitchen scale for checking reference loads

## Purchasing and safety notes

- Confirm the load cell is a **single four-wire full-bridge bar load cell** and confirm its mounting drawing. Do not assume wire colours without seller documentation.
- The HX711 is an interface/ADC, not a separate sensing modality.
- Confirm the VL53L0X breakout supports 3.3 V I²C operation.
- Use a phototransistor receiver rather than a demodulating remote-control receiver module.
- The load cell measures the reaction at one support, not the entire bridge load.
- Mechanical stops should prevent overload or permanent bending of the deck/load cell.
- Recheck ESP32 GPIO logic levels; do not feed 5 V logic directly into a GPIO.
