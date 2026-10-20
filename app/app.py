import argparse
import atexit
import logging
import signal
import sys
from typing import Optional

from flask import Flask, jsonify, make_response, render_template

from serial_reader import SerialReader

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [DashboardApp] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("DashboardApp")

app = Flask(__name__)
reader: Optional[SerialReader] = None


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/readings")
def get_readings():
    if reader is None:
        data = {
            "heart_rate": None,
            "spo2": None,
            "temperature": None,
            "humidity": None,
            "connected": False,
            "sensor_available": False,
            "finger_detected": False,
            "stale": True,
            "last_update": None,
            "seconds_since_update": None,
            "last_beat": None,
            "message": "Serial reader is not initialized.",
            "port": None,
            "stats": {},
        }
    else:
        data = reader.get_readings()

    response = make_response(jsonify(data))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/ports")
def get_available_ports():
    ports = SerialReader.list_ports()
    candidates = SerialReader.find_esp8266_candidates()
    return jsonify(
        {
            "all_ports": ports,
            "esp8266_candidates": candidates,
            "active_port": reader.port if reader else None,
        }
    )


def cleanup():
    global reader
    if reader is not None:
        logger.info("Stopping serial reader...")
        reader.stop()
        reader = None


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Smart Healthcare Monitoring System - Local Dashboard",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port connected to the ESP8266 (e.g., /dev/cu.usbserial-A5069RR4).",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Serial baud rate (default: 115200).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host interface (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=5050,
        help="Local HTTP port for the web dashboard (default: 5050).",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List discovered serial ports and exit.",
    )
    parser.add_argument(
        "--no-serial",
        action="store_true",
        help="Run web interface without opening a serial port.",
    )
    return parser.parse_args()


def main():
    global reader
    args = parse_arguments()

    if args.list_ports:
        print("\n========================================================")
        print(" Discovered Serial Ports on macOS")
        print("========================================================")
        all_ports = SerialReader.list_ports()
        candidates = SerialReader.find_esp8266_candidates()

        if not all_ports:
            print("No serial ports discovered.")
        else:
            for p in all_ports:
                marker = " [Likely ESP8266/USB-UART]" if p in candidates else ""
                print(f"Port: {p['device']}{marker}")
                print(f"  Description: {p['description']}")
                print(f"  Hardware ID: {p['hwid']}\n")

        print("To start with a specific port:")
        print("  python app.py --port /dev/cu.usbserial-XXXX")
        print("========================================================\n")
        sys.exit(0)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

    target_port = args.port

    if args.no_serial:
        logger.info("Running in --no-serial mode.")
    else:
        if not target_port:
            detected, status_reason = SerialReader.auto_detect_port()
            if detected:
                target_port = detected
                logger.info("Auto-selected port: %s (%s)", target_port, status_reason)
            else:
                logger.warning("Auto-detection: %s", status_reason)

        reader = SerialReader(port=target_port, baudrate=args.baud)
        reader.start()

    dashboard_url = f"http://{args.host}:{args.server_port}"
    print("\n" + "=" * 65)
    print(" SMART HEALTHCARE MONITORING SYSTEM")
    print(f" Dashboard URL : {dashboard_url}")
    print(f" Serial Port   : {target_port or 'Not assigned (Auto-detecting...)'}")
    print(f" Baud Rate     : {args.baud}")
    print(" Press Ctrl+C in this terminal to stop the server.")
    print("=" * 65 + "\n")

    app.run(
        host=args.host,
        port=args.server_port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
