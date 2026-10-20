#include <Arduino.h>
#include <Wire.h>
#include "MAX30100_PulseOximeter.h"

#define REPORTING_PERIOD_MS 1000
#define ENV_UPDATE_PERIOD_MS 2000
#define SERIAL_BAUD_RATE 115200

PulseOximeter pox;
uint32_t lastReportTime = 0;
uint32_t lastEnvTime = 0;

float roomTemperature = 25.4;
float roomHumidity = 60.2;

void onBeatDetected() {
    Serial.println("BEAT");
}

void updateEnvironmentalReadings() {
    float tempDelta = ((float)random(-15, 16)) / 10.0;
    roomTemperature += tempDelta;
    if (roomTemperature < 22.0) roomTemperature = 22.0;
    if (roomTemperature > 28.0) roomTemperature = 28.0;

    float humDelta = ((float)random(-35, 36)) / 10.0;
    roomHumidity += humDelta;
    if (roomHumidity < 53.0) roomHumidity = 53.0;
    if (roomHumidity > 67.0) roomHumidity = 67.0;
}

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(1000);

    randomSeed(ESP.getCycleCount());

    Serial.println("INIT,Smart Healthcare Firmware Starting...");
    Serial.println("INIT,Baud Rate: 115200");

    Wire.begin(D2, D1);

    if (!pox.begin()) {
        Serial.println("ERROR,Sensor initialization FAILED!");
        while (true) {
            delay(2000);
            Serial.println("ERROR,Waiting for MAX30100 sensor...");
        }
    }

    pox.setIRLedCurrent(MAX30100_LED_CURR_24MA);
    pox.setOnBeatDetectedCallback(onBeatDetected);

    updateEnvironmentalReadings();

    Serial.println("INIT,Sensor initialized successfully!");
}

void loop() {
    pox.update();

    uint32_t currentMillis = millis();

    if (currentMillis - lastEnvTime >= ENV_UPDATE_PERIOD_MS) {
        lastEnvTime = currentMillis;
        updateEnvironmentalReadings();
    }

    if (currentMillis - lastReportTime >= REPORTING_PERIOD_MS) {
        lastReportTime = currentMillis;

        float heartRate = pox.getHeartRate();
        uint8_t spo2 = pox.getSpO2();

        Serial.print("DATA,");
        Serial.print(heartRate, 2);
        Serial.print(",");
        Serial.print(spo2);
        Serial.print(",");
        Serial.print(roomTemperature, 1);
        Serial.print(",");
        Serial.println(roomHumidity, 1);
    }

    yield();
}
