# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Drive Google Earth directly with a deterministic synthetic route.

This intentionally bypasses the ORC message bus and navigation runtime.  Its
job is to answer one question cleanly: can the existing Earth geolocation
bridge make the embedded Google Earth instance move when fed changing fixes?
"""

from __future__ import annotations

import argparse
import math
import time

from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_input_camera_controller import EarthInputCameraController

_EARTH_RADIUS_M = 6_378_137.0
_ROUTE = (
    (42.802800, -83.012700),
    (42.803900, -83.012650),
    (42.804650, -83.011550),
    (42.804250, -83.010100),
    (42.803100, -83.009650),
    (42.802250, -83.010700),
    (42.802800, -83.012700),
)


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def _bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )
    return math.degrees(math.atan2(y, x)) % 360.0


def _wait_for_watch(bridge: EarthGeolocationBridge, timeout_s: float) -> int:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        count = bridge.registration_count()
        if count is not None and count > 0:
            return count
        time.sleep(0.1)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive the current Google Earth tab directly, bypassing the ORC bus."
    )
    parser.add_argument("--rate-hz", type=float, default=5.0)
    parser.add_argument("--speed-mps", type=float, default=10.0)
    parser.add_argument("--watch-timeout", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.rate_hz <= 0.0:
        raise SystemExit("--rate-hz must be > 0")
    if args.speed_mps <= 0.0:
        raise SystemExit("--speed-mps must be > 0")

    bridge = EarthGeolocationBridge()
    earth_input = EarthInputCameraController()

    print("[earth-direct] checking Google Earth DevTools target")
    if not earth_input.available():
        print("[earth-direct] FAIL: Google Earth DevTools target is not available on port 9223")
        return 2

    print("[earth-direct] installing ORC geolocation bridge")
    if not bridge.install():
        print("[earth-direct] FAIL: could not install geolocation bridge")
        return 3

    start = _ROUTE[0]
    heading = _bearing_deg(_ROUTE[0], _ROUTE[1])
    if not bridge.push_position(
        start[0], start[1], accuracy_m=1.5, heading_deg=heading, speed_m_s=args.speed_mps
    ):
        print("[earth-direct] FAIL: initial position was rejected by the bridge")
        return 4

    count = bridge.registration_count() or 0
    if count == 0:
        candidates = earth_input.location_control_diagnostics()
        if candidates:
            print("[earth-direct] location-like Earth controls discovered:")
            for candidate in candidates:
                print(f"[earth-direct]   {candidate}")
        else:
            print("[earth-direct] no location-like accessibility controls discovered")

        print("[earth-direct] Earth has no geolocation watch yet; activating Locate Me once")
        if not earth_input.activate_location_tracking():
            print("[earth-direct] FAIL: could not activate Earth's location control")
            return 5
        count = _wait_for_watch(bridge, args.watch_timeout)

    if count == 0:
        print("[earth-direct] FAIL: Earth never registered navigator.geolocation.watchPosition")
        print("[earth-direct] Locate Me was clicked, but Earth did not subscribe to geolocation.")
        print("[earth-direct] This remains isolated to Earth location activation/bridge integration.")
        return 6

    print(f"[earth-direct] PASS: Earth registered {count} geolocation watch(es)")
    print("[earth-direct] streaming route directly to Earth; Ctrl-C to stop")

    period_s = 1.0 / args.rate_hz
    segment_index = 0
    progress_m = 0.0
    sample = 0

    try:
        while True:
            a = _ROUTE[segment_index]
            b = _ROUTE[segment_index + 1]
            length_m = max(0.1, _distance_m(a, b))
            t = min(1.0, progress_m / length_m)
            lat = a[0] + (b[0] - a[0]) * t
            lon = a[1] + (b[1] - a[1]) * t
            heading = _bearing_deg(a, b)

            if not bridge.push_position(
                lat,
                lon,
                accuracy_m=1.5,
                heading_deg=heading,
                speed_m_s=args.speed_mps,
            ):
                print("[earth-direct] FAIL: Earth bridge stopped accepting positions")
                return 7

            if sample % max(1, round(args.rate_hz)) == 0:
                print(
                    f"[earth-direct] fix lat={lat:.6f} lon={lon:.6f} "
                    f"heading={heading:05.1f} speed={args.speed_mps:.1f}m/s"
                )

            sample += 1
            progress_m += args.speed_mps * period_s
            while progress_m >= length_m:
                progress_m -= length_m
                segment_index += 1
                if segment_index >= len(_ROUTE) - 1:
                    segment_index = 0
                a = _ROUTE[segment_index]
                b = _ROUTE[segment_index + 1]
                length_m = max(0.1, _distance_m(a, b))

            time.sleep(period_s)
    except KeyboardInterrupt:
        print("\n[earth-direct] stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
