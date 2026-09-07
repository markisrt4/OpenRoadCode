# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish a repeatable driving route for Google Earth navigation testing."""

from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timezone

from controllers.navigation.navigation_state import (
    GroundMotionState,
    NavigationState,
    PositionState,
)
from hardware_io.imu import Vector3
from messaging.contracts.navigation import NavigationStatePublisher
from messaging.zeromq import ZeroMqPublisher

_EARTH_RADIUS_M = 6_378_137.0

# Small synthetic loop centered near the existing Romeo navigation test origin.
# It is intentionally deterministic so Earth follow/chase behavior is easy to
# reproduce without needing a live GNSS receiver or Android sensor bridge.
_ROUTE = (
    (42.802800, -83.012700),
    (42.803900, -83.012650),
    (42.804650, -83.011550),
    (42.804250, -83.010100),
    (42.803100, -83.009650),
    (42.802250, -83.010700),
    (42.802800, -83.012700),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a deterministic simulated driving route for ORC Earth testing."
    )
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    parser.add_argument("--rate-hz", type=float, default=5.0)
    parser.add_argument("--speed-mps", type=float, default=10.0)
    parser.add_argument("--loop", action="store_true", default=True)
    return parser.parse_args()


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


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def main() -> None:
    args = parse_args()
    if args.rate_hz <= 0.0:
        raise SystemExit("--rate-hz must be > 0")
    if args.speed_mps <= 0.0:
        raise SystemExit("--speed-mps must be > 0")

    transport = ZeroMqPublisher(args.endpoint)
    publisher = NavigationStatePublisher(transport, source="earth-route-simulator")
    period_s = 1.0 / args.rate_hz
    segment_index = 0
    segment_progress_m = 0.0
    previous_heading_deg: float | None = None
    sample_index = 0

    print(
        "[earth-route] publishing synthetic route "
        f"to {args.endpoint} at {args.rate_hz:.1f} Hz, {args.speed_mps:.1f} m/s"
    )
    print("[earth-route] Ctrl-C to stop")

    try:
        while True:
            start = _ROUTE[segment_index]
            end = _ROUTE[segment_index + 1]
            segment_length_m = max(0.1, _distance_m(start, end))
            heading_deg = _bearing_deg(start, end)
            t = min(1.0, segment_progress_m / segment_length_m)
            lat = _lerp(start[0], end[0], t)
            lon = _lerp(start[1], end[1], t)

            # Give the attitude overlay something visible but plausible to do.
            turn_delta_deg = 0.0
            if previous_heading_deg is not None:
                turn_delta_deg = ((heading_deg - previous_heading_deg + 180.0) % 360.0) - 180.0
            roll_deg = max(-12.0, min(12.0, turn_delta_deg * 0.6))
            pitch_deg = 2.0 * math.sin(sample_index * 0.08)
            yaw_rate = math.radians(turn_delta_deg) * args.rate_hz

            now = datetime.now(timezone.utc)
            position = PositionState(
                received_at=now,
                latitude_deg=lat,
                longitude_deg=lon,
                altitude_m=250.0,
                fix_mode=3,
                satellites_visible=14,
                satellites_used=10,
                accuracy_m=1.5,
                source="earth-route-simulator",
                is_cached=False,
            )
            motion = GroundMotionState(
                received_at=now,
                speed_mps=args.speed_mps,
                course_deg=heading_deg,
                speed_accuracy_mps=0.1,
                course_accuracy_deg=1.0,
                source="earth-route-simulator",
            )
            state = NavigationState(
                timestamp=now,
                heading_deg=heading_deg,
                pitch_deg=pitch_deg,
                roll_deg=roll_deg,
                acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
                linear_acceleration_mps2=Vector3(0.0, 0.0, 0.0),
                angular_velocity_rad_s=Vector3(0.0, 0.0, yaw_rate),
                position=position,
                ground_motion=motion,
            )
            publisher.publish(state)

            previous_heading_deg = heading_deg
            sample_index += 1
            segment_progress_m += args.speed_mps * period_s
            if segment_progress_m >= segment_length_m:
                segment_progress_m -= segment_length_m
                segment_index += 1
                if segment_index >= len(_ROUTE) - 1:
                    segment_index = 0

            time.sleep(period_s)
    except KeyboardInterrupt:
        print("\n[earth-route] stopped")
    finally:
        transport.close()


if __name__ == "__main__":
    main()
