# Hardware Wiring Guide

## Project: Smart Healthcare Monitoring System
**Microcontroller:** ESP8266 NodeMCU (ESP-12E / v2)  
**Sensor:** MAX30100 Pulse Oximeter & Heart-Rate Sensor  

---

## 1. Pin-to-Pin Connection Table

| MAX30100 Module Pin | ESP8266 NodeMCU Pin | NodeMCU GPIO Number | Function / Notes |
|:---|:---|:---|:---|
| **VIN / VCC** | **3V3** (or **VIN/5V**)* | 3.3V Power | Power supply to sensor module |
| **GND** | **GND** | Ground | Common reference ground |
| **SDA** | **D2** | **GPIO 4** | I2C Serial Data line |
| **SCL** | **D1** | **GPIO 5** | I2C Serial Clock line |
| **INT** | *(Unconnected)* | - | Optional hardware interrupt (not needed in polling mode) |
| **IRD** | *(Unconnected)* | - | Photodiode test point (leave floating) |
| **RD** | *(Unconnected)* | - | Photodiode test point (leave floating) |

> [!IMPORTANT]
> **Power Supply Note (\*):**  
> Most MAX30100 breakout modules include onboard Low-Dropout (LDO) voltage regulators designed to step 5V or 3.3V down to the 1.8V core voltage required by the MAX30100 IC.
> If your module has a 3.3V regulator onboard, connect **VIN** to the NodeMCU's **3V3** pin. If your breakout explicitly requires 5V for its onboard regulator, connect to **VIN** (USB 5V). Never feed more voltage than specified on your specific breakout board.

---

## 2. Schematic Diagram

```
       +-----------------------+              +-----------------------+
       |    ESP8266 NodeMCU    |              |    MAX30100 Sensor    |
       |                       |              |                       |
       |                   3V3 +------------->+ VIN                   |
       |                   GND +------------->+ GND                   |
       |              GPIO4/D2 +<------------>+ SDA                   |
       |              GPIO5/D1 +------------->+ SCL                   |
       |                       |              |                       |
       |                       |              | INT  (NC)             |
       |                       |              | IRD  (NC)             |
       |                       |              | RD   (NC)             |
       +-----------+-----------+              +-----------------------+
                   |
                   | Micro-USB Cable
                   v
       +-----------------------+
       |   MacBook (macOS)     |
       | Python / Web Server   |
       +-----------------------+
```

---

## 3. Important Hardware Considerations

### A. I2C Pull-Up Resistors
- The I2C protocol requires pull-up resistors on both the **SDA** and **SCL** lines.
- Many third-party MAX30100 breakout boards (often generic purple boards marked `RC` or `GY-MAX30100`) have onboard 4.7kΩ pull-up resistors tied to their 1.8V rail instead of 3.3V. While some ESP8266 chips tolerate this, others fail during `pox.begin()`.
- If your sensor repeatedly reports `ERROR, Sensor initialization FAILED!`:
  1. Verify your jumper wire continuity with a multimeter.
  2. Ensure the wires are firmly seated in the breadboard / header pins. Loose ground or SDA/SCL lines are the #1 cause of I2C communication failures.

### B. Physical Sensor Placement
- The MAX30100 uses sensitive optical photoplethysmography (dual red and infrared LEDs + photodetector).
- **Placement Technique:** Place the fleshy pad of your index finger gently over the optical window.
- **Avoid Excessive Pressure:** Pressing too hard will occlude capillary blood flow in the fingertip, resulting in zero pulse signal or reading errors.
- **Ambient Light:** Avoid aiming high-intensity desk lamps directly at the exposed photodiode during measurement.
