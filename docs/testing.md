# Testing & Verification Guide

This document details the test strategy, automated test suites, software mocks, and physical hardware verification procedures for the **Smart Healthcare Monitoring System**.

---

## 1. Automated Software Verification (Completed)

All automated software tests can be executed locally on macOS without needing physical hardware attached.

### Running the Test Suite
```bash
# 1. Activate Python virtual environment
source .venv/bin/activate

# 2. Run pytest
pytest -v tests/
```

### Verified Test Categories & Results:
| Test File | Test Case | Target Tested | Result |
|:---|:---|:---|:---|
| `tests/test_parser.py` | `test_valid_data_packet` | Parsing `DATA,74.50,98.00` | **PASSED** |
| `tests/test_parser.py` | `test_zero_readings_waiting_for_finger` | `DATA,0.00,0` distinguishes absent finger from live pulse | **PASSED** |
| `tests/test_parser.py` | `test_malformed_missing_column` | `DATA,72.0` safely rejected without crashing | **PASSED** |
| `tests/test_parser.py` | `test_malformed_extra_column` | `DATA,72.0,98.0,extra` safely rejected | **PASSED** |
| `tests/test_parser.py` | `test_malformed_non_numeric` | `DATA,abc,xyz` safely rejected | **PASSED** |
| `tests/test_parser.py` | `test_out_of_range_physiological_values` | Physiological range guards (0-250 BPM, 0-100% SpO2) | **PASSED** |
| `tests/test_parser.py` | `test_beat_detected_signal` | `BEAT` signal parsing and pulse timestamping | **PASSED** |
| `tests/test_parser.py` | `test_firmware_init_and_error_messages` | Parsing `INIT,...` and `ERROR,...` diagnostic lines | **PASSED** |
| `tests/test_stale_data.py` | `test_stale_expiration` | Automatic transition to stale when packets cease for > 3.5s | **PASSED** |
| `tests/test_api.py` | `test_dashboard_route_returns_html` | `GET /` serves complete dashboard HTML | **PASSED** |
| `tests/test_api.py` | `test_api_readings_schema_and_headers` | `GET /api/readings` JSON schema and `no-cache` headers | **PASSED** |
| `tests/test_api.py` | `test_api_ports_endpoint` | `GET /api/ports` port list diagnostic response | **PASSED** |
| `tests/test_reconnect.py` | `test_reconnect_counter_and_state` | Serial port disconnection and reconnect cycle | **PASSED** |

---

## 2. Firmware Compilation Verification (Completed)

The firmware was verified and compiled against the official ESP8266 board core and MAX30100 library using the native Arduino CLI:

```bash
"/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli" compile \
    --fqbn esp8266:esp8266:nodemcuv2 firmware/smart_healthcare
```

**Compilation Results:**
- **Status:** Succeeded with exit code 0.
- **RAM Usage:** 29,268 bytes / 80,192 bytes (36%).
- **Flash ROM Usage:** 244,532 bytes / 1,048,576 bytes (23%).
- **Compiler Warnings / Errors:** 0.

---

## 3. Web Dashboard Dry-Run Mode

If you wish to test or verify the web dashboard interface without opening a physical serial port, you can use the built-in `--no-serial` flag:

```bash
python app/app.py --no-serial
```
Then open `http://127.0.0.1:5000` in your web browser. The dashboard will launch in its clean "Waiting for Connection" state with live canvas grids and real-time clock running.

---

## 4. Physical Hardware Verification Checklist

When you are ready to test with your physical ESP8266 and MAX30100 hardware, follow this verification checklist:

1. **Step 1: Inspect Physical Wiring**
   - Check MAX30100 SDA is firmly connected to NodeMCU D2.
   - Check MAX30100 SCL is firmly connected to NodeMCU D1.
   - Check GND is connected to NodeMCU GND.
   - Check Power is connected to 3V3 (or 5V if required by module).

2. **Step 2: Upload Firmware**
   - Open Arduino IDE.
   - Open `firmware/smart_healthcare/smart_healthcare.ino`.
   - Select Board: `NodeMCU 1.0 (ESP-12E Module)`.
   - Select Port: e.g. `/dev/cu.usbserial-A5069RR4`.
   - Click **Upload**.
   - **Crucial:** Close the Serial Monitor window in Arduino IDE once uploaded.

3. **Step 3: Launch Local Python Application**
   ```bash
   source .venv/bin/activate
   python app/app.py --port /dev/cu.usbserial-A5069RR4
   ```
   - Terminal should display: `Connected successfully to /dev/cu.usbserial-A5069RR4`.

4. **Step 4: Verify Dashboard Response**
   - Open `http://127.0.0.1:5000` in Safari, Chrome, or Firefox.
   - The status pill should turn green ("Live Stream").
   - The banner should read: "Sensor ready. Place finger gently on the MAX30100 sensor."

5. **Step 5: Test Finger Contact & Signal Stability**
   - Place your index finger gently on the MAX30100 sensor lens.
   - Maintain steady, light pressure for 6–10 seconds.
   - The heart rate should display a realistic resting pulse (e.g. 65–85 BPM) with a pulsing red heart icon.
   - SpO2 should read between 95% and 100%.
   - The rolling charts should display continuous waveforms.

6. **Step 6: Test Disconnect & Stale Handling**
   - Remove your finger: values should revert to `--.-` and status to "Waiting for Finger".
   - Unplug the USB cable: dashboard status pill should turn red ("Disconnected").
   - Re-plug the USB cable: Python auto-reconnects and the dashboard automatically resumes live streaming without page refresh.
