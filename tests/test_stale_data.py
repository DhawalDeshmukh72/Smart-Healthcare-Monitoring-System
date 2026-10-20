"""
Unit tests for Stale Data detection and lifecycle in SerialReader.
Verifies that sensor readings expire cleanly when packets cease arriving.
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from serial_reader import SerialReader


class TestStaleDataDetection(unittest.TestCase):
    def test_stale_expiration(self):
        # Configure short stale threshold (0.4s) for unit test speed
        reader = SerialReader(port="/dev/null", stale_threshold=0.4)

        # Before any packets, data is stale / unavailable
        initial = reader.get_readings()
        self.assertTrue(initial["stale"])
        self.assertIsNone(initial["last_update"])

        # Feed a valid reading
        reader.parse_line("DATA,72.00,98.00")
        live = reader.get_readings()
        self.assertFalse(live["stale"])
        self.assertTrue(live["finger_detected"])
        self.assertEqual(live["heart_rate"], 72.0)

        # Wait past the threshold
        time.sleep(0.5)

        # Now readings should be flagged stale
        expired = reader.get_readings()
        self.assertTrue(expired["stale"])
        # Finger detected is set to False when stale to prevent showing stale readings as active
        self.assertFalse(expired["finger_detected"])
        self.assertGreater(expired["seconds_since_update"], 0.4)

        # Receiving a fresh packet recovers the live state immediately
        reader.parse_line("DATA,73.50,97.00")
        recovered = reader.get_readings()
        self.assertFalse(recovered["stale"])
        self.assertTrue(recovered["finger_detected"])
        self.assertEqual(recovered["heart_rate"], 73.50)


if __name__ == "__main__":
    unittest.main()
