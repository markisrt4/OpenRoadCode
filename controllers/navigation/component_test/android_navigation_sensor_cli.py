# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise Android bridge IMU data through NavigationSensorIf."""

from __future__ import annotations

import time

from controllers.navigation.android_navigation_sensor import AndroidNavigationSensor


def main() -> int:
    sensor = AndroidNavigationSensor()
    print("[*] Connecting to OpenRoadCode Android sensor bridge...")
    sensor.connect()
    print("[*] Connected. Reading IMU at 10 Hz. Press Ctrl+C to stop.")
    try:
        while True:
            sample = sensor.read_motion()
            print(
                f"accel={sample.acceleration_mps2} "
                f"gyro={sample.angular_velocity_rad_s}"
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
    finally:
        sensor.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
