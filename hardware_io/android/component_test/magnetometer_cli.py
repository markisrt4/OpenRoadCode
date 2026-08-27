# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise the Android phone magnetometer through hardware_io."""

from __future__ import annotations

import math
import time

from hardware_io.android import AndroidMagnetometer, AndroidSensorBridgeClient


def main() -> int:
    magnetometer = AndroidMagnetometer(AndroidSensorBridgeClient())
    print("[*] Connecting to OpenRoadCode Android magnetometer...")
    magnetometer.connect()
    print("[*] Connected. Reading at 10 Hz. Rotate the phone to exercise all axes.")
    print("[*] Press Ctrl+C to stop.")
    try:
        while True:
            sample = magnetometer.read_magnetometer()
            field = sample.magnetic_field_ut
            magnitude = math.sqrt(field.x**2 + field.y**2 + field.z**2)
            print(
                f"mag=({field.x:8.2f}, {field.y:8.2f}, {field.z:8.2f}) uT "
                f"|B|={magnitude:8.2f} uT timestamp_ns={sample.timestamp_ns}",
                flush=True,
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
    finally:
        magnetometer.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
