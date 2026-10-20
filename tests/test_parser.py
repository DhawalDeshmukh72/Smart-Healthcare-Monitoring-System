"""
Unit tests for SerialReader packet parsing and error resilience.
Verifies that valid packets are extracted, malformed packets are safely rejected,
and diagnostic / heartbeat signals are correctly processed.
"""

import os
import sys
import unittest

# Ensure app package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from serial_reader import SerialReader


class TestSerialParser(unittest.TestCase):
    def setUp(self):
        self.reader = SerialReader(port="/dev/null", baudrate=115200)

    def test_valid_data_packet(self):
        """Verify normal DATA packet parsing."""
        success = self.reader.parse_line("DATA,74.50,98.00")
        self.assertTrue(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["heart_rate"], 74.50)
        self.assertEqual(readings["spo2"], 98.00)
        self.assertTrue(readings["sensor_available"])
        self.assertTrue(readings["finger_detected"])
        self.assertFalse(readings["stale"])
        self.assertEqual(readings["stats"]["packets_received"], 1)
        self.assertEqual(readings["stats"]["packets_malformed"], 0)

    def test_zero_readings_waiting_for_finger(self):
        """In MAX30100, 0.0 means waiting for finger or acquiring signal."""
        success = self.reader.parse_line("DATA,0.00,0")
        self.assertTrue(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["heart_rate"], 0.0)
        self.assertEqual(readings["spo2"], 0.0)
        self.assertTrue(readings["sensor_available"])
        self.assertFalse(readings["finger_detected"])
        self.assertIn("Place finger", readings["message"])

    def test_malformed_missing_column(self):
        """Verify packet with insufficient fields is rejected without crashing."""
        success = self.reader.parse_line("DATA,72.0")
        self.assertFalse(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["stats"]["packets_malformed"], 1)

    def test_valid_4_and_5_field_packet(self):
        """Verify DATA packet with temperature and humidity."""
        success = self.reader.parse_line("DATA,76.50,97.00,26.4,58.2")
        self.assertTrue(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["heart_rate"], 76.50)
        self.assertEqual(readings["spo2"], 97.00)
        self.assertEqual(readings["temperature"], 26.4)
        self.assertEqual(readings["humidity"], 58.2)

    def test_text_environmental_format(self):
        """Verify plain-text environmental output from existing Arduino sketches."""
        self.reader.parse_line("Temperature: 27.2 C")
        self.reader.parse_line("Humidity: 57.5 %")
        readings = self.reader.get_readings()
        self.assertEqual(readings["temperature"], 27.2)
        self.assertEqual(readings["humidity"], 57.5)

    def test_malformed_extra_column(self):
        """Verify packet with non-numeric extra fields is rejected."""
        success = self.reader.parse_line("DATA,72.0,98.0,invalid_temp")
        self.assertFalse(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["stats"]["packets_malformed"], 1)

    def test_malformed_non_numeric(self):
        """Verify non-numeric string values do not cause uncaught exceptions."""
        success = self.reader.parse_line("DATA,invalid_hr,98.0")
        self.assertFalse(success)

        readings = self.reader.get_readings()
        self.assertEqual(readings["stats"]["packets_malformed"], 1)

    def test_out_of_range_physiological_values(self):
        """Verify out-of-range sensor spikes are rejected."""
        # Unrealistic HR (e.g. 500 BPM)
        self.assertFalse(self.reader.parse_line("DATA,500.0,98.0"))
        # Unrealistic SpO2 (e.g. 150%)
        self.assertFalse(self.reader.parse_line("DATA,72.0,150.0"))
        # Negative values
        self.assertFalse(self.reader.parse_line("DATA,-10.0,98.0"))

        readings = self.reader.get_readings()
        self.assertEqual(readings["stats"]["packets_malformed"], 3)

    def test_beat_detected_signal(self):
        """Verify BEAT triggers last_beat timestamp without failing."""
        self.assertFalse(self.reader.parse_line("BEAT"))
        readings = self.reader.get_readings()
        self.assertIsNotNone(readings["last_beat"])

    def test_firmware_init_and_error_messages(self):
        """Verify INIT and ERROR diagnostics update message state."""
        self.reader.parse_line("INIT,Sensor initialized successfully!")
        readings = self.reader.get_readings()
        self.assertIn("Sensor initialized successfully!", readings["message"])
        self.assertTrue(readings["sensor_available"])

        self.reader.parse_line("ERROR,Sensor initialization FAILED!")
        readings = self.reader.get_readings()
        self.assertIn("Sensor initialization FAILED!", readings["message"])
        self.assertFalse(readings["sensor_available"])


if __name__ == "__main__":
    unittest.main()
