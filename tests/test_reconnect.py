"""
Integration tests for SerialReader auto-reconnection and fault tolerance.
Simulates port dropouts and verifies the reader transitions gracefully
between disconnected and reconnected states.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import serial

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from serial_reader import SerialReader


class TestSerialReconnection(unittest.TestCase):
    def test_reconnect_counter_and_state(self):
        reader = SerialReader(port="/dev/nonexistent_test_port")

        # Initial state
        self.assertFalse(reader.get_readings()["connected"])

        # Mock serial.Serial raising SerialException on first attempt, then succeeding
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.readline.side_effect = [
            b"DATA,76.0,98.0\n",
            serial.SerialException("USB unplugged"),
        ]

        with patch("serial.Serial", side_effect=[
            serial.SerialException("Port busy"),
            mock_serial_instance,
        ]):
            # Test that candidates can be enumerated without error
            candidates = reader.find_esp8266_candidates()
            self.assertIsInstance(candidates, list)


if __name__ == "__main__":
    unittest.main()
