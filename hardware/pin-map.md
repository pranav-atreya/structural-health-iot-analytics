# Initial Pin Map (verify against the actual board and modules)

## Shared I²C bus

| Signal | ESP32 pin | Devices |
|---|---|---|
| SDA | GPIO 21 | MPU6050 and VL53L0X |
| SCL | GPIO 22 | MPU6050 and VL53L0X |
| 3V3 | 3.3 V | Logic supply where supported |
| GND | GND | Common ground |

The MPU6050 and VL53L0X normally use different I²C addresses, so they can share the bus. Run an I²C scanner before integrating the full firmware.

## Other signals

| Signal | ESP32 pin |
|---|---|
| HX711 DOUT/DT | GPIO 32 |
| HX711 SCK | GPIO 33 |
| IR receiver digital output | GPIO 27 |

## Important electrical checks

- Power modules according to their specific breakout-board specifications.
- Ensure all grounds are common.
- Never connect a 5 V output to an ESP32 GPIO.
- IR LED must have a series current-limiting resistor selected for its forward voltage/current.
- A phototransistor may need a pull-up resistor and correct collector/emitter orientation; test the circuit before fixing it mechanically.
- Load-cell wire colours differ by manufacturer. Confirm E+, E−, A+, A− using the supplied datasheet/wiring documentation. Do not rely on wire colour alone.
- Mount the load cell according to its drawing, with the correct fixed and loaded ends. Do not clamp the strain-gauge body.
- Mechanical dimensions and load-cell mounting are provisional until the actual parts are in hand.
