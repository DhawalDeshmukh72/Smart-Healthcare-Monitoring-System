# System Troubleshooting Guide

This guide covers common issues and exact diagnostic steps for the **Smart Healthcare Monitoring System** on macOS with ESP8266 and MAX30100.

---

### 1. ESP8266 Not Detected by macOS
- **Symptom:** Running `ls /dev/cu.*` does not show any `usbserial` or `wchusbserial` devices.
- **Likely Cause:** 
  1. The USB cable is a "charge-only" cable lacking the D+/D- data lines.
  2. The USB-to-UART bridge chip driver (CH340 or CP2102) is not installed on macOS.
- **Solution:**
  - Swap the USB cable with a known data-sync cable.
  - Check System Information (`Apple Menu -> About This Mac -> More Info -> System Report -> USB`). If you see a device like "CP2102 USB to UART Bridge Controller" or "USB-Serial Controller", macOS sees the hardware.
  - For CH340 boards, install the signed macOS CH34x driver if not natively recognized by macOS 12+.

---

### 2. Incorrect Serial Port Specified
- **Symptom:** Terminal outputs `serial.serialutil.SerialException: [Errno 2] could not open port /dev/cu.xxx: [Errno 2] No such file or directory`.
- **Solution:**
  - Discover the exact active port name:
    ```bash
    python -m serial.tools.list_ports -v
    ```
  - Common macOS port patterns:
    - `/dev/cu.usbserial-A5069RR4` (FTDI chip)
    - `/dev/cu.usbserial-XXXX`
    - `/dev/cu.wchusbserialXXXX` (CH340 chip)
    - `/dev/cu.SLAB_USBtoUART` (Silicon Labs CP2102)
  - Launch the server with the discovered port:
    ```bash
    python app/app.py --port /dev/cu.usbserial-A5069RR4
    ```

---

### 3. Permission or Port-Access Errors
- **Symptom:** `PermissionError: [Errno 13] Permission denied: '/dev/cu.xxx'`.
- **Solution:**
  - In macOS, device files in `/dev/cu.*` generally have `crw-rw-rw-` permissions.
  - If another process has an exclusive lock, macOS reports a resource busy error (see item 4).
  - Verify terminal permissions or run `ls -l /dev/cu.usbserial*`.

---

### 4. Arduino Serial Monitor Still Holding the Port
- **Symptom:** `SerialException: [Errno 16] Resource busy: '/dev/cu.usbserial-xxxx'`.
- **Likely Cause:** The Arduino IDE Serial Monitor or another terminal program (Screen, Minicom, PlatformIO) is currently connected to the ESP8266. Serial ports cannot be opened by multiple applications simultaneously.
- **Solution:**
  1. Close the Serial Monitor window in Arduino IDE (or click the toggle button in the top right).
  2. Identify and terminate any process holding the port:
     ```bash
     lsof | grep -i usbserial
     ```
  3. Re-run `python app/app.py`.

---

### 5. Python Cannot Import Flask
- **Symptom:** `ModuleNotFoundError: No module named 'flask'`.
- **Solution:**
  - Ensure your virtual environment is activated:
    ```bash
    source .venv/bin/activate
    ```
  - Verify Flask installation:
    ```bash
    pip install -r requirements.txt
    ```

---

### 6. Python Cannot Import Serial
- **Symptom:** `ModuleNotFoundError: No module named 'serial'`.
- **Solution:**
  - Install `pyserial` (do **not** install the deprecated package named `serial`):
    ```bash
    pip install pyserial
    ```

---

### 7. Dashboard Page Does Not Open
- **Symptom:** Browser displays `ERR_CONNECTION_REFUSED` or cannot reach `http://127.0.0.1:5000`.
- **Solution:**
  1. Confirm that `python app/app.py` is actively running in a terminal window.
  2. Confirm you are browsing to `http://127.0.0.1:5000` (or `http://localhost:5000`).
  3. Ensure port 5000 is not blocked by macOS firewall or another local server (e.g., AirPlay Receiver on macOS Sonoma/Sequoia sometimes uses port 5000; AirPlay can be disabled under `System Settings -> General -> AirDrop & AirPlay -> AirPlay Receiver`).
  4. If port 5000 is occupied, run on another port:
     ```bash
     python app/app.py --server-port 5050
     ```

---

### 8. API Returns No Sensor Readings
- **Symptom:** Navigating to `http://127.0.0.1:5000/api/readings` shows `null` readings or `"connected": false`.
- **Solution:**
  - Verify the ESP8266 is plugged in and recognized.
  - Check the terminal where `app.py` is running. Look for diagnostic messages like `Auto-selected ESP8266 serial port` or `Serial disconnected`.
  - Check that the firmware was uploaded with the correct baud rate (`115200`).

---

### 9. Serial Data Cannot Be Parsed
- **Symptom:** Dashboard telemetry displays incrementing `Malformed Lines` count.
- **Solution:**
  - Ensure the baud rate matches between ESP8266 firmware and Python (`115200`). A baud rate mismatch produces garbled ASCII characters.
  - Check that your uploaded firmware uses the formatted output: `DATA,<heart_rate>,<spo2>`.

---

### 10. Heart-Rate Values Remain Zero (`0.00 BPM`)
- **Symptom:** The dashboard connects and receives `DATA,0.00,0` records, but heart rate never rises above 0.
- **Likely Cause:**
  1. **Finger Contact:** The finger is not placed on the sensor, or is pressing too hard, blocking blood flow in the capillaries.
  2. **Wait for Acquisition:** The MAX30100 algorithm requires approximately 4–8 seconds of continuous, steady contact to calculate the peak-to-peak pulse intervals.
  3. **Timing Blocking in Firmware:** If any `delay()` or Wi-Fi operations were added to the firmware, `pox.update()` cannot poll the sensor FIFO frequently enough.
- **Solution:**
  - Rest your finger lightly on the optical window without squeezing.
  - Keep still for 6–10 seconds.
  - Verify that our non-blocking firmware `smart_healthcare.ino` is running.

---

### 11. SpO2 Values Remain Zero (`0%`)
- **Likely Cause:** SpO2 calculation depends on computing the ratio of AC/DC absorbance between Red and Infrared light. When pulse peaks cannot be resolved, SpO2 defaults to 0.
- **Solution:**
  - Keep your hand warm and stable.
  - Avoid strong fluorescent or direct sunlight hitting the top of the sensor.

---

### 12. USB Disconnection During Operation
- **Symptom:** USB cable was accidentally unplugged or bumped.
- **Behavior & Recovery:**
  - The Python reader automatically catches the `SerialException`, updates status to `Disconnected`, marks the data stale, and enters an automatic retry loop every 2 seconds.
  - Simply plug the USB cable back in. Within 2–4 seconds, the Python reader will automatically detect the re-enumerated port and resume streaming without restarting the server!

---

### 13. Sensor Initialization Failure (`ERROR, Sensor initialization FAILED!`)
- **Likely Cause:**
  1. The ESP8266 cannot communicate over I2C with the MAX30100 at I2C address `0x57`.
  2. Wiring mismatch: `D2` is not wired to `SDA` or `D1` is not wired to `SCL`.
  3. The sensor is not receiving power, or pull-up voltage is missing.
- **Solution:**
  - Re-verify connections:
    - MAX30100 SDA -> ESP8266 Pin D2
    - MAX30100 SCL -> ESP8266 Pin D1
    - MAX30100 GND -> ESP8266 Pin GND
    - MAX30100 VIN -> ESP8266 Pin 3V3 (or 5V if required by your regulator board)
  - Ensure jumper cables make firm mechanical contact.

---

### 14. Arduino Firmware Compilation Errors
- **Symptom:** `fatal error: MAX30100_PulseOximeter.h: No such file or directory`.
- **Solution:**
  - Open Arduino IDE -> `Tools` -> `Manage Libraries...`.
  - Search for `MAX30100lib` by oxullo / Milan Neskovic and click **Install**.
  - Alternatively, if using `arduino-cli`:
    ```bash
    "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli" lib install "MAX30100lib"
    ```

---

### 15. Python Application Fails to Reconnect After USB Re-Plug
- **Symptom:** USB was unplugged and re-plugged, but Python keeps printing retry errors.
- **Likely Cause:** On macOS, when some USB-UART chips re-enumerate, the system increments the serial port suffix (e.g. from `usbserial-0001` to `usbserial-0002`).
- **Solution:**
  - If the port name changed, run `python app/app.py` with auto-detection or supply the updated `--port` name.
