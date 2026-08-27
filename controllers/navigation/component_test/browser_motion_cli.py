# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise browser DeviceMotion as an OpenRoadCode navigation sensor."""

from __future__ import annotations

import time

from services.navigation.browser_motion_source import BrowserMotionSource


def main() -> int:
    source = BrowserMotionSource()
    source.connect()
    print("[*] Waiting for browser motion. Press Ctrl+C to stop.", flush=True)
    print(f"[*] Open: {source.url}", flush=True)

    previous_count = 0
    previous_time = time.monotonic()
    try:
        while True:
            time.sleep(1.0)
            count = source.sample_count
            now = time.monotonic()
            rate = (count - previous_count) / (now - previous_time)
            previous_count = count
            previous_time = now
            try:
                motion = source.read_motion()
            except RuntimeError as exc:
                print(f"samples={count} rate={rate:.1f} Hz unavailable: {exc}", flush=True)
                continue
            age = source.sample_age_ms
            print(
                f"samples={count} rate={rate:.1f} Hz age={age:.1f} ms "
                f"accel={motion.acceleration_mps2} gyro={motion.angular_velocity_rad_s}",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\n[*] Stopping browser motion source...", flush=True)
    finally:
        source.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
