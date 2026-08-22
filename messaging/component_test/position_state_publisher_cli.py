# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish predictable mock navigation positions using the public contract."""

import argparse
import math
import time
from datetime import datetime, timezone

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import PositionStatePublisher
from messaging.zeromq import ZeroMqPublisher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish mock openroad.navigation.position messages."
    )
    parser.add_argument(
        "--endpoint",
        default="tcp://0.0.0.0:5557",
        help="ZeroMQ bind endpoint (default: tcp://0.0.0.0:5557)",
    )
    parser.add_argument(
        "--rate-hz",
        type=float,
        default=5.0,
        help="Publication rate in Hz (default: 5)",
    )
    parser.add_argument(
        "--fresh-hz",
        type=float,
        default=1.0,
        help="Rate at which the simulated sensor produces a new fix (default: 1)",
    )
    args = parser.parse_args()
    if args.rate_hz <= 0.0:
        parser.error("--rate-hz must be greater than zero")
    if args.fresh_hz <= 0.0:
        parser.error("--fresh-hz must be greater than zero")
    if args.fresh_hz > args.rate_hz:
        parser.error("--fresh-hz cannot exceed --rate-hz")
    return args


def main() -> None:
    args = parse_args()
    publisher = ZeroMqPublisher(args.endpoint)
    position_publisher = PositionStatePublisher(publisher)

    publication_period_s = 1.0 / args.rate_hz
    fresh_every = max(1, round(args.rate_hz / args.fresh_hz))
    phase = 0.0
    sample_index = 0
    state: PositionState | None = None

    print(
        f"Publishing mock {position_publisher.__class__.__name__} data on "
        f"{args.endpoint} at {args.rate_hz:g} Hz "
        f"({args.fresh_hz:g} Hz fresh fixes)"
    )

    try:
        while True:
            is_fresh = state is None or sample_index % fresh_every == 0
            if is_fresh:
                state = PositionState(
                    received_at=datetime.now(timezone.utc),
                    latitude_deg=42.8028 + 0.001 * math.sin(phase),
                    longitude_deg=-83.0127 + 0.001 * math.cos(phase),
                    altitude_m=250.0 + 2.0 * math.sin(phase / 2.0),
                    speed_mps=13.4 + 1.5 * math.sin(phase),
                    course_deg=(90.0 + math.degrees(phase)) % 360.0,
                    fix_mode=3,
                    satellites_visible=14,
                    satellites_used=10,
                    accuracy_m=2.5,
                    source="mock",
                    is_cached=False,
                )
                phase += 0.08
            else:
                state = PositionState(
                    received_at=state.received_at,
                    latitude_deg=state.latitude_deg,
                    longitude_deg=state.longitude_deg,
                    altitude_m=state.altitude_m,
                    speed_mps=state.speed_mps,
                    course_deg=state.course_deg,
                    fix_mode=state.fix_mode,
                    satellites_visible=state.satellites_visible,
                    satellites_used=state.satellites_used,
                    accuracy_m=state.accuracy_m,
                    source=state.source,
                    is_cached=True,
                )

            position_publisher.publish(state)
            sample_index += 1
            time.sleep(publication_period_s)
    except KeyboardInterrupt:
        pass
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
