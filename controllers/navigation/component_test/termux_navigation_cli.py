# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise Android GNSS and IMU inputs through Termux:API."""

from __future__ import annotations

import argparse
import threading
import time

from controllers.navigation.termux_navigation_sensor import TermuxNavigationSensor
from controllers.navigation.termux_position_source import TermuxPositionSource


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Termux:API navigation inputs")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    args = parser.parse_args()

    sensor = TermuxNavigationSensor()
    position = TermuxPositionSource(interval_seconds=args.interval)
    latest_position = None
    position_lock = threading.Lock()

    def on_position(state) -> None:
        nonlocal latest_position
        with position_lock:
            latest_position = state

    sensor.connect()
    position.start(on_position)
    print("[*] Termux navigation sources running. Press Ctrl+C to stop.")

    try:
        while True:
            started = time.monotonic()
            motion = sensor.read_motion()
            elapsed_ms = (time.monotonic() - started) * 1000.0
            with position_lock:
                gps = latest_position

            print(
                f"accel={motion.acceleration_mps2} "
                f"gyro={motion.angular_velocity_rad_s} "
                f"read={elapsed_ms:.0f} ms"
            )
            if gps is not None:
                print(
                    f"gps=({gps.latitude_deg}, {gps.longitude_deg}) "
                    f"alt={gps.altitude_m}m speed={gps.speed_mps}m/s "
                    f"course={gps.course_deg}deg accuracy={gps.accuracy_m}m"
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        position.stop()
        sensor.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
