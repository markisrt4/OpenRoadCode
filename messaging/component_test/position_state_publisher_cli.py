# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish predictable mock position and derived motion messages."""

import argparse
import math
import time
from datetime import datetime, timezone
from controllers.navigation.navigation_state import PositionState
from messaging.contracts.common.timestamp import encode_timestamp
from messaging.contracts.navigation import MOTION_STATE_TOPIC, PositionStatePublisher, encode_motion_state
from messaging.zeromq import ZeroMqPublisher


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    parser.add_argument("--rate-hz", type=float, default=5.0)
    parser.add_argument("--fresh-hz", type=float, default=1.0)
    return parser.parse_args()


def main():
    args = parse_args()
    publisher = ZeroMqPublisher(args.endpoint)
    position_publisher = PositionStatePublisher(publisher)
    period = 1.0 / args.rate_hz
    fresh_every = max(1, round(args.rate_hz / args.fresh_hz))
    phase = 0.0
    sample_index = 0
    state = None
    motion = None
    try:
        while True:
            fresh = state is None or sample_index % fresh_every == 0
            if fresh:
                now = datetime.now(timezone.utc)
                altitude = 250.0 + 20.0 * math.sin(phase / 2.0)
                vertical_speed = 1.6 * math.cos(phase / 2.0)
                speed = 13.4 + 4.0 * math.sin(phase)
                heading = (math.pi / 2 + phase) % (2 * math.pi)
                state = PositionState(
                    received_at=now,
                    latitude_deg=42.8028 + 0.01 * math.sin(phase),
                    longitude_deg=-83.0127 + 0.01 * math.cos(phase),
                    altitude_m=altitude,
                    speed_mps=speed,
                    course_deg=math.degrees(heading),
                    fix_mode=3, satellites_visible=14, satellites_used=10,
                    accuracy_m=2.5, source="mock", is_cached=False,
                )
                motion = encode_motion_state(
                    timestamp=encode_timestamp(now), source="mock-estimator",
                    heading_rad=heading, ground_speed_m_s=speed,
                    vertical_speed_m_s=vertical_speed, turn_rate_rad_s=0.08,
                    is_cached=False,
                )
                phase += 0.08
            else:
                state = PositionState(
                    received_at=state.received_at, latitude_deg=state.latitude_deg,
                    longitude_deg=state.longitude_deg, altitude_m=state.altitude_m,
                    speed_mps=state.speed_mps, course_deg=state.course_deg,
                    fix_mode=state.fix_mode, satellites_visible=state.satellites_visible,
                    satellites_used=state.satellites_used, accuracy_m=state.accuracy_m,
                    source=state.source, is_cached=True,
                )
                motion = {**motion, "data": {**motion["data"], "is_cached": True}}
            position_publisher.publish(state)
            publisher.publish(MOTION_STATE_TOPIC, motion)
            sample_index += 1
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
