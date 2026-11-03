# ESP32 Firmware

Owner under the internal working arrangement: Pranav, with mechanical and test coordination from Yash.

## Planned firmware responsibilities

- Initialize the MPU6050 and VL53L0X on the shared I²C bus.
- Read the HX711 load-cell amplifier.
- Count IR break-beam interruptions without double-counting a single vehicle.
- Produce a timestamped measurement window.
- Derive vibration RMS/peak, baseline-relative deflection, calibrated support reaction and cumulative vehicle count.
- Publish the four agreed values to ThingSpeak over MQTT.

## Agreed initial pins

- I²C SDA: GPIO 21
- I²C SCL: GPIO 22
- HX711 DOUT: GPIO 32
- HX711 SCK: GPIO 33
- IR receiver digital output: GPIO 27

Verify actual module pin labels and voltage requirements before powering the circuit. Keep credentials in a local secrets/config file excluded from Git.

Firmware is intentionally not committed yet; add tested code here as development proceeds.
