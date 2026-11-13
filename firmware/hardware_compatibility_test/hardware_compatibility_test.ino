#include <Wire.h>
#include "HX711.h"

// ==========================================
// PIN CONFIGURATION
// ==========================================

#define SDA_PIN 21
#define SCL_PIN 22

#define IR1_PIN 26
#define IR2_PIN 27

#define HX_DT  32
#define HX_SCK 33

// ==========================================
// MPU6050 / MPU6500
// ==========================================

uint8_t mpuAddress = 0;
bool mpuReady = false;

int16_t mpuData[7] = {0};

bool readRegister(uint8_t address, uint8_t reg,
                  uint8_t &value) {

  Wire.beginTransmission(address);
  Wire.write(reg);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(address, (uint8_t)1) != 1) {
    return false;
  }

  value = Wire.read();
  return true;
}

bool writeRegister(uint8_t address, uint8_t reg,
                   uint8_t value) {

  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);

  return Wire.endTransmission() == 0;
}

bool initialiseMPU() {

  uint8_t identity;

  if (readRegister(0x68, 0x75, identity)) {
    mpuAddress = 0x68;
  }
  else if (readRegister(0x69, 0x75, identity)) {
    mpuAddress = 0x69;
  }
  else {
    return false;
  }

  Serial.print("MPU address: 0x");
  Serial.println(mpuAddress, HEX);

  Serial.print("WHO_AM_I: 0x");
  Serial.println(identity, HEX);

  if (identity != 0x68 && identity != 0x70) {
      Serial.println("Unknown IMU identity!");
      return false;
  }

  Serial.println(
      identity == 0x70 ?
      "MPU-6500 DETECTED!" :
      "MPU-6050 DETECTED!"
  );

  // Wake up MPU6050
  if (!writeRegister(mpuAddress, 0x6B, 0x00)) {
    return false;
  }

  delay(100);

  // Sample rate divider
  writeRegister(mpuAddress, 0x19, 9);

  // Digital low-pass filter
  writeRegister(mpuAddress, 0x1A, 0x03);

  // Gyroscope: +/- 500 degrees/sec
  writeRegister(mpuAddress, 0x1B, 0x08);

  // Accelerometer: +/- 4g
  writeRegister(mpuAddress, 0x1C, 0x08);

  return true;
}

bool readMPU() {

  Wire.beginTransmission(mpuAddress);
  Wire.write(0x3B);

  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(mpuAddress, (uint8_t)14) != 14) {
    return false;
  }

  for (int i = 0; i < 7; i++) {

    uint8_t highByte = Wire.read();
    uint8_t lowByte = Wire.read();

    mpuData[i] =
      (int16_t)((highByte << 8) | lowByte);
  }

  return true;
}

// ==========================================
// HX711
// ==========================================

HX711 scale;

bool hxReady = false;
bool hxHasReading = false;

long hxZero = 0;
long hxRaw = 0;
long hxNet = 0;

float hxFiltered = 0;

void tareLoadCell() {

  if (!hxReady) {
    Serial.println("HX711 unavailable.");
    return;
  }

  Serial.println("\nTARE STARTED");
  Serial.println("Remove all additional load.");

  if (!scale.wait_ready_timeout(3000)) {
    Serial.println("HX711 NOT READY");
    return;
  }

  hxZero = scale.read_average(10);

  hxRaw = hxZero;
  hxNet = 0;
  hxFiltered = 0;

  hxHasReading = true;

  Serial.print("New zero offset: ");
  Serial.println(hxZero);

  Serial.println("TARE COMPLETE\n");
}

// ==========================================
// IR SENSORS
// ==========================================

int previousIR1 = -1;
int previousIR2 = -1;

void checkIR(int ir1, int ir2) {

  unsigned long now = millis();

  if (ir1 != previousIR1) {

    Serial.print("IR_EVENT,");
    Serial.print(now);
    Serial.print(",SENSOR_1,");

    Serial.println(ir1 == HIGH ? "HIGH" : "LOW");

    previousIR1 = ir1;
  }

  if (ir2 != previousIR2) {

    Serial.print("IR_EVENT,");
    Serial.print(now);
    Serial.print(",SENSOR_2,");

    Serial.println(ir2 == HIGH ? "HIGH" : "LOW");

    previousIR2 = ir2;
  }
}

// ==========================================
// SETUP
// ==========================================

void setup() {

  Serial.begin(115200);
  delay(1500);

  Serial.println("\n======================================");
  Serial.println(" STRUCTURAL HEALTH IoT");
  Serial.println(" FULL HARDWARE COMPATIBILITY TEST");
  Serial.println("======================================");

  pinMode(IR1_PIN, INPUT);
  pinMode(IR2_PIN, INPUT);

  // Initialise I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  delay(200);

  // MPU6050
  Serial.println("\n[1] INITIALISING MPU6050");

  mpuReady = initialiseMPU();

  Serial.println(mpuReady ?
    "MPU6050: ONLINE" :
    "MPU6050: FAILED");

  // HX711
  Serial.println("\n[2] INITIALISING HX711");

  scale.begin(HX_DT, HX_SCK);

  hxReady = scale.wait_ready_timeout(5000);

  if (hxReady) {

    Serial.println("HX711: ONLINE");

    Serial.println(
      "Keep the load cell unloaded for tare."
    );

    tareLoadCell();

  } else {

    Serial.println("HX711: FAILED");
  }

  // IR modules
  Serial.println("\n[3] IR MODULES");

  previousIR1 = digitalRead(IR1_PIN);
  previousIR2 = digitalRead(IR2_PIN);

  Serial.print("IR 1 initial state: ");
  Serial.println(previousIR1);

  Serial.print("IR 2 initial state: ");
  Serial.println(previousIR2);

  // Sensor summary
  Serial.println("\n======================================");
  Serial.println(" HARDWARE INITIALISATION SUMMARY");
  Serial.println("======================================");

  Serial.print("MPU6050: ");
  Serial.println(mpuReady ? "PASS" : "FAIL");

  Serial.print("HX711: ");
  Serial.println(hxReady ? "PASS" : "FAIL");

  Serial.println("IR modules: GPIO INPUTS ACTIVE");

  Serial.println("\nCommands:");
  Serial.println("T = Tare load cell (no additional load)");
  Serial.println("======================================");

  Serial.println(
    "\ntime_ms,ax_g,ay_g,az_g,"
    "gx_dps,gy_dps,gz_dps,"
    "hx_raw,hx_net,hx_filtered,ir1,ir2"
  );
}

// ==========================================
// MAIN LOOP
// ==========================================

void loop() {

  // Serial commands
  while (Serial.available()) {

    char command = Serial.read();

    if (command == 'T' || command == 't') {
      tareLoadCell();
    }
  }

  // Read IR continuously
  int ir1 = digitalRead(IR1_PIN);
  int ir2 = digitalRead(IR2_PIN);

  checkIR(ir1, ir2);

  // Read HX711 whenever a conversion is ready
  if (hxReady && scale.is_ready()) {

    hxRaw = scale.read();

    hxNet = hxRaw - hxZero;

    if (!hxHasReading) {

      hxFiltered = hxNet;
      hxHasReading = true;

    } else {

      hxFiltered =
        0.25f * hxNet +
        0.75f * hxFiltered;
    }
  }

  // Refresh MPU at 100 Hz
  static unsigned long lastMPU = 0;

  if (mpuReady && micros() - lastMPU >= 10000) {

    lastMPU = micros();

    if (!readMPU()) {
      Serial.println("MPU_READ_ERROR");
    }
  }

  // Print combined data at 10 Hz
  static unsigned long lastOutput = 0;

  if (millis() - lastOutput >= 100) {

    lastOutput = millis();

    Serial.print(millis());

    Serial.print(",");

    if (mpuReady) {

      Serial.print(mpuData[0] / 8192.0f, 4);
      Serial.print(",");
      Serial.print(mpuData[1] / 8192.0f, 4);
      Serial.print(",");
      Serial.print(mpuData[2] / 8192.0f, 4);
      Serial.print(",");
      Serial.print(mpuData[4] / 65.5f, 3);
      Serial.print(",");
      Serial.print(mpuData[5] / 65.5f, 3);
      Serial.print(",");
      Serial.print(mpuData[6] / 65.5f, 3);

    } else {

      Serial.print("NA,NA,NA,NA,NA,NA");
    }

    Serial.print(",");

    if (hxReady && hxHasReading) {
      Serial.print(hxRaw);
      Serial.print(",");
      Serial.print(hxNet);
      Serial.print(",");
      Serial.print(hxFiltered, 2);
    } else {
      Serial.print("NA,NA,NA");
    }

    Serial.print(",");
    Serial.print(ir1);

    Serial.print(",");
    Serial.println(ir2);
  }
}
