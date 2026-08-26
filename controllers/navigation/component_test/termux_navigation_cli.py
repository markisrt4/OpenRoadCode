# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise Android GNSS and IMU inputs through Termux:API."""

from __future__ import annotations

import argparse
import threading
import time

from controllers.navigation.termux_navigation_adapter import TermuxNavigationAdapter
from controllers.navigation.termux_position_adapter import TermuxPositionAdapter
from hardware_io.termux_api import TermuxLocationClient, TermuxSensorClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Termux:API navigation inputs")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    args = parser.parse_args()

    print("[*] Creating Termux:API clients...", flush=True)
    sensor_client = TermuxSensorClient()
    location_client = TermuxLocationClient()
    sensor = TermuxNavigationAdapter(sensor_client)
    position = TermuxPositionAdapter(location_client, interval_seconds=args.interval)
    latest_position = None
    position_lock = threading.Lock()

    def on_position(state) -> None:
        nonlocal latest_position
        with position_lock:
            latest_position = state

    print(f"[*] termux-sensor available:   {sensor_client.is_available}", flush=True)
    print(f"[*] termux-location available: {location_client.is_available}", flush=True)
    print("[*] Connecting motion adapter...", flush=True)
    sensor.connect()
    print("[*] Starting position adapter...", flush=True)
    position.start(on_position)
    print("[*] Termux navigation sources running. Press Ctrl+C to stop.", flush=True)

    try:
        while True:
            print("[*] Reading accelerometer + gyroscope...", flush=True)
            started = time.monotonic()
            motion = sensor.read_motion()
            elapsed_ms = (time.monotonic() - started) * 1000.0
            with position_lock:
                gps = latest_position

            print(
                f"accel={motion.acceleration_mps2} "
                f"gyro={motion.angular_velocity_rad_s} "
                f"read={elapsed_ms:.0f} ms",
                flush=True,
            )
            if gps is not None:
                print(
                    f"gps=({gps.latitude_deg}, {gps.longitude_deg}) "
                    f"alt={gps.altitude_m}m speed={gps.speed_mps}m/s "
                    f"course={gps.course_deg}deg accuracy={gps.accuracy_m}m",
                    flush=True,
                )
            else:
                print("gps=(waiting for first location fix)", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        position.stop()
        sensor.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
