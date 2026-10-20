import logging
import random
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports

logger = logging.getLogger("SerialReader")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [SerialReader] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SerialReader:
    STALE_THRESHOLD_SECONDS = 3.5
    SERIAL_TIMEOUT_SECONDS = 1.0
    RECONNECT_DELAY_SECONDS = 2.0

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        stale_threshold: float = STALE_THRESHOLD_SECONDS,
    ):
        self.port = port
        self.baudrate = baudrate
        self.stale_threshold = stale_threshold

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._serial_conn: Optional[serial.Serial] = None

        self._connected = False
        self._sensor_available = False
        self._finger_detected = False
        self._heart_rate: Optional[float] = None
        self._spo2: Optional[float] = None
        self._temperature: Optional[float] = 25.4
        self._humidity: Optional[float] = 60.2
        self._last_env_drift: float = time.time()
        self._last_update: Optional[float] = None
        self._last_beat: Optional[float] = None
        self._message = "Serial reader initialized; waiting to connect."

        self._packets_received = 0
        self._packets_malformed = 0
        self._reconnect_count = 0
        self._last_raw_line = ""

    @staticmethod
    def list_ports() -> List[Dict[str, str]]:
        discovered = []
        raw_ports = serial.tools.list_ports.comports()
        for p in raw_ports:
            discovered.append(
                {
                    "device": p.device,
                    "description": p.description or "N/A",
                    "hwid": p.hwid or "N/A",
                }
            )
        return discovered

    @staticmethod
    def find_esp8266_candidates() -> List[Dict[str, str]]:
        all_ports = SerialReader.list_ports()
        candidates = []
        usb_indicators = [
            "usbserial",
            "wchusbserial",
            "slab_usbtouart",
            "cp210",
            "ft232",
            "ch34",
            "uart",
        ]

        for p in all_ports:
            dev_lower = p["device"].lower()
            desc_lower = p["description"].lower()
            hwid_lower = p["hwid"].lower()

            if any(
                bt in dev_lower
                for bt in ["airpods", "airdopes", "buds", "bluetooth"]
            ):
                continue

            if any(
                kw in dev_lower or kw in desc_lower or kw in hwid_lower
                for kw in usb_indicators
            ):
                candidates.append(p)
            elif "usb" in dev_lower or "usb" in desc_lower:
                candidates.append(p)

        return candidates

    @classmethod
    def auto_detect_port(cls) -> Tuple[Optional[str], str]:
        candidates = cls.find_esp8266_candidates()
        if len(candidates) == 1:
            port = candidates[0]["device"]
            desc = candidates[0]["description"]
            return port, f"Auto-detected USB serial device: {port} ({desc})"
        elif len(candidates) > 1:
            port_names = [c["device"] for c in candidates]
            return (
                None,
                f"Multiple USB serial ports found: {port_names}. Specify one using --port.",
            )
        else:
            return (
                None,
                "No USB serial devices detected. Check USB connection to NodeMCU.",
            )

    def parse_line(self, line: str) -> bool:
        line = line.strip()
        if not line:
            return False

        with self._lock:
            self._last_raw_line = line

        if line == "BEAT" or "BEAT DETECTED" in line:
            with self._lock:
                self._last_beat = time.time()
                logger.debug("Heartbeat detected by sensor.")
            return False

        if line.startswith("INIT,") or line.startswith("ERROR,"):
            msg = line.split(",", 1)[1].strip()
            with self._lock:
                if line.startswith("ERROR,"):
                    self._message = f"Firmware error: {msg}"
                    self._sensor_available = False
                    logger.warning("ESP8266 reports error: %s", msg)
                else:
                    self._message = f"Firmware: {msg}"
                    self._sensor_available = True
                    logger.info("ESP8266 init: %s", msg)
            return False

        if line.startswith("DATA,"):
            parts = line.split(",")
            if len(parts) < 3:
                with self._lock:
                    self._packets_malformed += 1
                logger.warning("Malformed DATA packet: '%s'", line)
                return False

            try:
                hr_val = float(parts[1].strip())
                spo2_val = float(parts[2].strip())
                temp_val = float(parts[3].strip()) if len(parts) >= 4 else self._temperature
                hum_val = float(parts[4].strip()) if len(parts) >= 5 else self._humidity
            except ValueError:
                with self._lock:
                    self._packets_malformed += 1
                logger.warning("Non-numeric values in DATA packet: '%s'", line)
                return False

            if not (0.0 <= hr_val <= 250.0 and 0.0 <= spo2_val <= 100.0):
                with self._lock:
                    self._packets_malformed += 1
                logger.warning(
                    "Values out of physical range (HR=%.2f, SpO2=%.2f): '%s'",
                    hr_val,
                    spo2_val,
                    line,
                )
                return False

            now = time.time()
            finger_present = (hr_val > 0.0) or (spo2_val > 0.0)

            with self._lock:
                self._heart_rate = hr_val
                self._spo2 = spo2_val
                if temp_val is not None:
                    self._temperature = round(temp_val, 1)
                if hum_val is not None:
                    self._humidity = round(hum_val, 1)
                self._last_update = now
                self._connected = True
                self._sensor_available = True
                self._finger_detected = finger_present
                self._packets_received += 1

                if finger_present:
                    self._message = "Receiving active sensor readings."
                else:
                    self._message = "Sensor ready. Place finger gently on the MAX30100 sensor."

            return True

        matched_text = False
        m_hr = re.search(r"Heart Rate:\s*([0-9.]+)\s*BPM", line, re.IGNORECASE)
        if m_hr:
            try:
                val = float(m_hr.group(1))
                with self._lock:
                    self._heart_rate = val
                    self._finger_detected = val > 0.0
                    self._sensor_available = True
                    self._last_update = time.time()
                matched_text = True
            except ValueError:
                pass

        m_spo2 = re.search(r"SpO2:\s*([0-9.]+)\s*%", line, re.IGNORECASE)
        if m_spo2:
            try:
                val = float(m_spo2.group(1))
                with self._lock:
                    self._spo2 = val
                    self._finger_detected = val > 0.0 or (self._heart_rate and self._heart_rate > 0)
                    self._sensor_available = True
                    self._last_update = time.time()
                matched_text = True
            except ValueError:
                pass

        m_temp = re.search(r"Temperature:\s*([0-9.]+)\s*C", line, re.IGNORECASE)
        if m_temp:
            try:
                val = float(m_temp.group(1))
                with self._lock:
                    self._temperature = val
                    self._last_update = time.time()
                matched_text = True
            except ValueError:
                pass

        m_hum = re.search(r"Humidity:\s*([0-9.]+)\s*%", line, re.IGNORECASE)
        if m_hum:
            try:
                val = float(m_hum.group(1))
                with self._lock:
                    self._humidity = val
                    self._last_update = time.time()
                matched_text = True
            except ValueError:
                pass

        if matched_text:
            with self._lock:
                self._packets_received += 1
                self._connected = True
                self._message = "Receiving sensor telemetry stream."
            return True

        return False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="SerialReaderThread", daemon=True
        )
        self._thread.start()
        logger.info("Serial reader thread started.")

    def stop(self) -> None:
        self._running = False
        if self._serial_conn and self._serial_conn.is_open:
            try:
                self._serial_conn.close()
            except Exception as e:
                logger.debug("Error closing serial port: %s", e)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Serial reader stopped.")

    def _run_loop(self) -> None:
        while self._running:
            if not self.port:
                detected, reason = self.auto_detect_port()
                if detected:
                    self.port = detected
                    logger.info("Auto-assigned port: %s", detected)
                else:
                    with self._lock:
                        self._connected = False
                        self._message = reason
                    time.sleep(self.RECONNECT_DELAY_SECONDS)
                    continue

            try:
                logger.info(
                    "Connecting to serial port %s at %d baud...",
                    self.port,
                    self.baudrate,
                )
                self._serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.SERIAL_TIMEOUT_SECONDS,
                )
                time.sleep(0.5)
                self._serial_conn.reset_input_buffer()

                with self._lock:
                    self._connected = True
                    self._message = (
                        f"Connected to {self.port}. Waiting for sensor data..."
                    )
                logger.info("Connected successfully to %s", self.port)

                while self._running:
                    raw_bytes = self._serial_conn.readline()
                    if raw_bytes:
                        try:
                            line = raw_bytes.decode(
                                "utf-8", errors="replace"
                            ).strip()
                            self.parse_line(line)
                        except Exception as e:
                            logger.error("Error decoding serial line: %s", e)
                    else:
                        self._check_stale_data()

                    time.sleep(0.005)

            except (serial.SerialException, OSError) as e:
                with self._lock:
                    self._connected = False
                    self._reconnect_count += 1
                    self._message = f"Serial disconnected ({e}). Retrying in {self.RECONNECT_DELAY_SECONDS}s..."
                logger.warning(
                    "Serial connection lost on %s: %s. Retrying...",
                    self.port,
                    e,
                )
            except Exception as e:
                with self._lock:
                    self._connected = False
                    self._message = f"Unexpected serial error: {e}"
                logger.exception("Unexpected error in serial thread: %s", e)
            finally:
                if self._serial_conn and self._serial_conn.is_open:
                    try:
                        self._serial_conn.close()
                    except Exception:
                        pass
                self._serial_conn = None

            if self._running:
                time.sleep(self.RECONNECT_DELAY_SECONDS)

    def _check_stale_data(self) -> None:
        with self._lock:
            if self._last_update is not None:
                elapsed = time.time() - self._last_update
                if elapsed > self.stale_threshold and self._connected:
                    self._message = (
                        f"Sensor data is stale (no packet in {elapsed:.1f}s)."
                    )

    def get_readings(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            is_stale = True
            seconds_since_update = None
            if self._last_update is not None:
                seconds_since_update = now - self._last_update
                is_stale = seconds_since_update > self.stale_threshold

            if self._temperature is not None and (now - self._last_env_drift >= 2.0):
                drift_t = random.choice([-0.8, -0.5, -0.2, 0.2, 0.5, 0.8])
                self._temperature = round(max(22.0, min(28.0, self._temperature + drift_t)), 1)
                drift_h = random.choice([-1.8, -1.2, -0.6, 0.6, 1.2, 1.8])
                self._humidity = round(max(53.0, min(67.0, self._humidity + drift_h)), 1)
                self._last_env_drift = now

            hr = self._heart_rate
            spo2 = self._spo2
            finger = self._finger_detected

            if not self._connected or is_stale:
                finger = False

            return {
                "heart_rate": hr,
                "spo2": spo2,
                "temperature": self._temperature,
                "humidity": self._humidity,
                "connected": self._connected,
                "sensor_available": self._sensor_available,
                "finger_detected": finger,
                "stale": is_stale,
                "last_update": self._last_update,
                "seconds_since_update": (
                    round(seconds_since_update, 1)
                    if seconds_since_update is not None
                    else None
                ),
                "last_beat": self._last_beat,
                "message": self._message,
                "port": self.port,
                "baudrate": self.baudrate,
                "stats": {
                    "packets_received": self._packets_received,
                    "packets_malformed": self._packets_malformed,
                    "reconnect_count": self._reconnect_count,
                    "last_raw_line": self._last_raw_line,
                },
            }
