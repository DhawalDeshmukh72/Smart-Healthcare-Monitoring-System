# Smart Healthcare Monitoring System
### Real-Time Heart Rate & Blood Oxygen (SpO2) Monitor
**ESP8266 NodeMCU • MAX30100 • Python PySerial • Local Flask Dashboard**

---

## 1. Project Overview

This project is a complete, local, privacy-first **Smart Healthcare Monitoring System**. It continuously acquires physiological metrics from hardware sensors and streams them to a responsive real-time web dashboard running on your computer.

### Key Monitored Parameters
- **Heart Rate** in Beats Per Minute (BPM)
- **Blood Oxygen Saturation (SpO2)** as a percentage (%)
- **Ambient Room Temperature** (°C) & **Relative Humidity** (%)
- **Real-Time Pulse Beat Detection** with interactive canvas PPG waveforms

---

### System Architecture
```
+-------------------------------------------------------+
|  MAX30100 Pulse Oximeter                              |
|  Optical PPG (Red + Infrared LEDs & Photodetector)    |
+---------------------------+---------------------------+
                            | I2C (SDA = D2, SCL = D1)
                            v
+-------------------------------------------------------+
|  ESP8266 NodeMCU Firmware (smart_healthcare.ino)      |
|  Dedicated sensor loop: uninterrupted pox.update()    |
|  High-frequency hardware FIFO sampling (100 Hz)       |
|  No Wi-Fi / No HTTP blocking on microcontroller       |
+---------------------------+---------------------------+
                            | USB Serial @ 115200 Baud (CSV protocol)
                            v
+-------------------------------------------------------+
|  Host Computer Application (app/app.py)               |
|  Background PySerial Reader Thread                    |
|  Thread-safe state, auto-reconnect & stale detection  |
|  Flask REST API (http://127.0.0.1:5000)               |
+---------------------------+---------------------------+
                            | HTTP JSON API (/api/readings)
                            v
+-------------------------------------------------------+
|  Real-Time Web Dashboard (Browser)                    |
|  Pure HTML5, CSS3, & Native Canvas Line Charts        |
|  100% Offline • Zero Remote CDNs • Zero Cloud APIs    |
+-------------------------------------------------------+
```

### Why Dedicated Serial Communication?
On the ESP8266, running an asynchronous Wi-Fi stack or an embedded HTTP web server introduces network interrupts and blocking delays. The MAX30100 requires continuous, rapid sampling (`pox.update()`) of its 16-sample hardware FIFO register. Any timing jitter or blocking delay leads to FIFO overflow, missed pulse beats, and zeroed readings. By offloading networking, UI serving, and data processing entirely to the host computer over a high-speed 115200-baud USB serial link, the ESP8266 focuses 100% of its CPU cycles on precise sensor sampling.

---

## 2. Hardware Wiring

Connect the MAX30100 sensor module to your ESP8266 NodeMCU as follows:

| MAX30100 Pin | ESP8266 NodeMCU Pin | NodeMCU GPIO | Description |
|:---|:---|:---|:---|
| **VIN / VCC** | **3V3** (or **5V**)* | 3.3V / 5V | Power supply |
| **GND** | **GND** | GND | Ground reference |
| **SDA** | **D2** | GPIO 4 | I2C Serial Data |
| **SCL** | **D1** | GPIO 5 | I2C Serial Clock |

> [!NOTE]
> *Most RC522/MAX30100 breakout boards work reliably on **3V3**. If your module features an onboard 3.3V regulator that causes an I2C voltage drop, connect VIN to the **5V / VIN** pin of the NodeMCU. See [docs/wiring.md](file:///Users/dhawaldeshmukh72/Documents/Projects/IOT/docs/wiring.md) for full schematic details and pull-up resistor notes.*

---

## 3. How to Run the Firmware from Arduino IDE (Step-by-Step)

Follow these detailed steps to compile and flash the firmware to your ESP8266 using the official **Arduino IDE** (v1.8.x or v2.x):

### Step 3.1: Install Arduino IDE
If not already installed, download and install [Arduino IDE](https://www.arduino.cc/en/software) for macOS, Windows, or Linux.

### Step 3.2: Add ESP8266 Board Manager URL
1. Open **Arduino IDE**.
2. Go to **Arduino IDE -> Settings / Preferences** (macOS: `Cmd + ,` or Windows/Linux: `File -> Preferences`).
3. Locate the field **Additional Boards Manager URLs**.
4. Paste the following URL (if you have existing URLs, separate them with a comma):
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
5. Click **OK** to save preferences.

### Step 3.3: Install the ESP8266 Board Package
1. In Arduino IDE, navigate to **Tools -> Board -> Boards Manager...** (or click the board icon on the left sidebar in Arduino IDE 2.x).
2. In the search bar, type `esp8266`.
3. Locate **esp8266 by ESP8266 Community** and click **Install** (recommended version: `3.0.2` or later).
4. Wait for the installation to finish.

### Step 3.4: Install Required MAX30100 Library
1. In Arduino IDE, go to **Tools -> Manage Libraries...** (or click the Library icon on the left sidebar).
2. In the search bar, type `MAX30100lib`.
3. Locate **MAX30100lib by OXullo Intersecans**.
4. Click **Install**.

### Step 3.5: Open the Firmware Sketch
1. Go to **File -> Open...** (or `Cmd + O`).
2. Navigate to this repository directory:
   ```
   firmware/smart_healthcare/smart_healthcare.ino
   ```
3. Click **Open**.

### Step 3.6: Configure Board Settings & Select Port
Under the **Tools** menu, configure the following parameters:
- **Board:** `ESP8266 Boards` -> `NodeMCU 1.0 (ESP-12E Module)`
- **CPU Frequency:** `80 MHz` (or `160 MHz`)
- **Flash Size:** `4MB (FS:2MB OTA:~1019KB)`
- **Upload Speed:** `115200` (or `921600` for faster uploads)
- **Port:** Select your ESP8266 serial port:
  - **macOS:** `/dev/cu.usbserial-XXXX`, `/dev/cu.wchusbserialXXXX`, or `/dev/cu.SLAB_USBtoUART`
  - **Windows:** `COM3`, `COM4`, etc.
  - **Linux:** `/dev/ttyUSB0` or `/dev/ttyACM0`

### Step 3.7: Verify and Upload
1. Click the **Verify** button (check-mark icon `✓`) in the top toolbar to compile. Ensure it builds with zero errors.
2. Connect your ESP8266 to your computer using a micro-USB **data** cable.
3. Click the **Upload** button (right-arrow icon `➔`).
4. Watch the output console at the bottom until it displays `100% ... Leaving... Hard resetting via RTS pin...`. The firmware is now running!

### Step 3.8: CRITICAL: Close Arduino Serial Monitor
> [!IMPORTANT]
> **Ensure the Serial Monitor window in Arduino IDE is completely closed.**
> macOS, Windows, and Linux do not allow two programs to access the same serial COM port at the same time. If the Arduino Serial Monitor is open, the Python dashboard server will fail with `[Errno 16] Resource busy`.

---

## 4. How to Run the Project from Your IDE / Terminal

You can run the Python dashboard server using **VS Code**, **Cursor**, **PyCharm**, or any standard **Terminal**.

### Option A: Running from Visual Studio Code / Cursor
1. Open the project folder in VS Code (`File -> Open Folder...` -> Select `IOT`).
2. Open the integrated terminal (`Ctrl + ~` or Terminal -> New Terminal).
3. Set up and activate the Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # On macOS/Linux
   # or for Windows: .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Select Python Interpreter:
   - Press `Cmd + Shift + P` (or `Ctrl + Shift + P`), type `Python: Select Interpreter`, and select `.venv/bin/python`.
6. Run the application:
   - Either open `app/app.py` and click the **Run Python File** (Play icon `▶`) in the top-right corner, or run:
   ```bash
   python app/app.py
   ```

### Option B: Running from PyCharm
1. Open PyCharm and select **Open** -> choose the `IOT` folder.
2. Go to **Settings/Preferences -> Project: IOT -> Python Interpreter**.
3. Add or select the virtual environment at `.venv`.
4. Open the PyCharm Terminal and verify dependencies: `pip install -r requirements.txt`.
5. Right-click on `app/app.py` in the project tree and click **Run 'app'**.

### Option C: Running from Command Line / Terminal

#### Step 1: Open Terminal & Navigate to Project Directory
```bash
cd /Users/dhawaldeshmukh72/Documents/Projects/IOT
```

#### Step 2: Create & Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```
*(On Windows Command Prompt: `.venv\Scripts\activate`)*

#### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Identify the ESP8266 Serial Port
Plug your ESP8266 into your USB port and run:
```bash
python -m serial.tools.list_ports -v
```
Look for a device such as `/dev/cu.usbserial-A5069RR4` or `/dev/cu.wchusbserial1410`.

#### Step 5: Start the Python Dashboard Server
```bash
# Auto-detects connected ESP8266 serial port automatically:
python app/app.py

# Or specify your port explicitly:
python app/app.py --port /dev/cu.usbserial-A5069RR4

# Optional: Run on a custom HTTP port:
python app/app.py --server-port 5050
```

---

## 5. Live Dashboard Access & Sensor Placement

1. Once `app.py` is running, open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
2. Place your index finger gently and stably flat on the MAX30100 optical glass.
   > [!TIP]
   > **Proper Finger Pressure:** Pressing too hard blocks capillary blood flow; placing too lightly allows ambient light leakage. Apply light, steady pressure.
3. Within 5–8 seconds, the dashboard will update with:
   - **Heart Rate (BPM)** with pulsing beat animation
   - **Blood Oxygen (SpO2 %)** with status badges (Normal, Borderline, Low)
   - **Real-Time Pulse PPG Waveform** plotted on an interactive HTML5 canvas
   - **Connection Diagnostics:** Link latency, packet counters, and serial port status

To cleanly stop the application, press `Ctrl + C` in the terminal.

---

## 6. REST API Endpoints

The local Python server exposes REST endpoints for diagnostic or third-party client integration:

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/` | Serves the HTML5/CSS3/Canvas responsive dashboard |
| `GET` | `/api/readings` | Returns live sensor values, connection state, and packet stats |
| `GET` | `/api/ports` | Scans and lists all active system USB/serial devices |

### Sample JSON Output (`/api/readings`):
```json
{
    "heart_rate": 74.5,
    "spo2": 98.0,
    "room_temperature": 25.4,
    "room_humidity": 60.2,
    "connected": true,
    "sensor_available": true,
    "finger_detected": true,
    "stale": false,
    "last_update": 1729261234.56,
    "seconds_since_update": 0.8,
    "last_beat": 1729261234.12,
    "message": "Receiving active sensor readings.",
    "port": "/dev/cu.usbserial-A5069RR4",
    "baudrate": 115200,
    "stats": {
        "packets_received": 89,
        "packets_malformed": 0,
        "reconnect_count": 0
    }
}
```

---

## 7. Automated Testing Suite

The repository includes a comprehensive unit test suite covering serial packet parsing, physiological threshold validation, auto-reconnect logic, and API schema compliance:

```bash
source .venv/bin/activate
pytest -v tests/
```
All tests run with zero external hardware required using mock serial loopbacks.

---

## 8. Common Troubleshooting & FAQs

### Q1: `SerialException: [Errno 16] Resource busy: '/dev/cu.usbserial-xxxx'`
- **Cause:** The Arduino IDE Serial Monitor or another terminal instance is holding exclusive control over the serial device.
- **Solution:** Close the Serial Monitor window in Arduino IDE. If necessary, kill any hanging serial processes:
  ```bash
  lsof | grep -i usbserial
  ```

### Q2: `ERROR,Sensor initialization FAILED!` in Arduino Serial Monitor
- **Cause:** ESP8266 cannot communicate with the MAX30100 over I2C.
- **Solution:**
  1. Check wiring: `SDA -> D2 (GPIO 4)`, `SCL -> D1 (GPIO 5)`.
  2. Verify power: Try switching the MAX30100 `VIN` pin between `3V3` and `5V`.
  3. Pull-up resistors: Certain Chinese MAX30100 clones have incorrect onboard pull-up resistors connected to 1.8V instead of 3.3V. Adding two external 4.7kΩ pull-up resistors from SDA & SCL to 3.3V resolves this issue. See [docs/wiring.md](file:///Users/dhawaldeshmukh72/Documents/Projects/IOT/docs/wiring.md).

### Q3: `Port could not be found or opened` in Python
- **Solution:** Verify that your USB cable supports **data transfer** (not a charging-only cable). Run `python -m serial.tools.list_ports -v` to ensure the computer detects the board.

---

## 9. Educational Prototype Notice

> [!WARNING]
> This system is an **engineering and educational prototype** intended for academic demonstration, hobbyist experimentation, and pair-programming development. It is **not** an FDA-cleared, CE-marked, or clinically certified medical device. Never use its readings for clinical diagnostics, therapy, emergency decisions, or patient care.
