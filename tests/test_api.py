"""
Integration tests for Flask Web Server and JSON API endpoints.
Verifies response schemas, HTTP status codes, and strict cache headers.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

import app as flask_module
from serial_reader import SerialReader


class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        flask_module.app.config["TESTING"] = True
        self.client = flask_module.app.test_client()
        # Attach a mock reader
        self.mock_reader = SerialReader(port="/dev/test_port", baudrate=115200)
        flask_module.reader = self.mock_reader

    def tearDown(self):
        flask_module.reader = None

    def test_dashboard_route_returns_html(self):
        """GET / should serve the dashboard HTML with HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.content_type)
        html = response.data.decode("utf-8")
        self.assertIn("Smart Healthcare Monitoring", html)
        self.assertIn("heartRateChart", html)
        self.assertIn("spo2Chart", html)

    def test_api_readings_schema_and_headers(self):
        """GET /api/readings should return JSON adhering to required schema and no-cache headers."""
        # Inject known data
        self.mock_reader.parse_line("DATA,80.50,99.00")

        response = self.client.get("/api/readings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.content_type)

        # Check Cache-Control headers
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("no-cache", cache_control)

        # Parse JSON
        data = json.loads(response.data)
        required_keys = [
            "heart_rate",
            "spo2",
            "connected",
            "sensor_available",
            "finger_detected",
            "stale",
            "last_update",
            "message",
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' missing from API response")

        self.assertEqual(data["heart_rate"], 80.5)
        self.assertEqual(data["spo2"], 99.0)
        self.assertFalse(data["stale"])

    def test_api_ports_endpoint(self):
        """GET /api/ports returns discovered serial ports."""
        response = self.client.get("/api/ports")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("all_ports", data)
        self.assertIn("esp8266_candidates", data)


if __name__ == "__main__":
    unittest.main()
