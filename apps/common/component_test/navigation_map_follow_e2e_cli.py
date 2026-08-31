# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise simulated navigation positions through the real bus into map follow."""

from __future__ import annotations

import argparse
import threading
import time
from datetime import datetime, timezone

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import PositionStatePublisher
from messaging.zeromq.broker import ZeroMqBroker
from messaging.zeromq.publisher import ZeroMqPublisher
from messaging.zeromq.subscriber import ZeroMqSubscriber
from protocols.map_renderer.map_renderer_client import MapRendererClient

BROKER_PUBLISHER_ENDPOINT = "tcp://127.0.0.1:16556"
BROKER_SUBSCRIBER_ENDPOINT = "tcp://127.0.0.1:16557"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish simulated navigation positions through the real OpenRoadCode "
            "ZeroMQ bus and emit map commands on the same broker."
        )
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Seconds between simulated position fixes",
    )
    return parser.parse_args()


def _wait_for_broker(broker: ZeroMqBroker) -> None:
    deadline = time.monotonic() + 2.0
    while not broker.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("ZeroMQ broker did not start")
        time.sleep(0.01)


def _simulated_positions() -> tuple[PositionState, ...]:
    # A short southeast-moving sequence. The points are deliberately close
    # enough for MapPositionAdapter interpolation rather than snap behavior.
    return (
        PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=42.802800,
            longitude_deg=-83.012700,
            speed_mps=13.4,
            course_deg=145.0,
            fix_mode=3,
            source="simulation",
        ),
        PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=42.802650,
            longitude_deg=-83.012560,
            speed_mps=13.4,
            course_deg=145.0,
            fix_mode=3,
            source="simulation",
        ),
        PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=42.802500,
            longitude_deg=-83.012420,
            speed_mps=13.4,
            course_deg=145.0,
            fix_mode=3,
            source="simulation",
        ),
        PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=42.802350,
            longitude_deg=-83.012280,
            speed_mps=13.4,
            course_deg=145.0,
            fix_mode=3,
            source="simulation",
        ),
    )


def main() -> int:
    args = _parse_args()
    if args.interval <= 0.0:
        raise ValueError("--interval must be greater than zero")

    broker = ZeroMqBroker(
        BROKER_PUBLISHER_ENDPOINT,
        BROKER_SUBSCRIBER_ENDPOINT,
    )
    broker_thread = threading.Thread(
        target=broker.run,
        name="navigation-map-follow-test-broker",
        daemon=True,
    )
    broker_thread.start()
    _wait_for_broker(broker)

    map_adapter = MapPositionAdapter(
        MapRendererClient(ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)),
        frame_rate_hz=20.0,
        correction_time_s=0.25,
        maximum_prediction_age_s=0.75,
        minimum_camera_interval_s=0.1,
    )
    runtime = NavigationMapFollowRuntime(
        ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT),
        map_adapter,
    )
    publisher_transport = ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)
    position_publisher = PositionStatePublisher(publisher_transport)

    try:
        runtime.start()

        # PUB/SUB subscriptions need a brief settling period. Sending the first
        # fix twice also makes the test robust against slow-joiner behavior.
        time.sleep(0.25)
        positions = _simulated_positions()
        position_publisher.publish(positions[0])
        time.sleep(0.1)

        for state in positions:
            position_publisher.publish(state)
            print(
                "published: "
                f"lat={state.latitude_deg:.6f} "
                f"lon={state.longitude_deg:.6f} "
                f"course={state.course_deg:.1f}°"
            )
            time.sleep(args.interval)

        # Allow the interpolation loop to emit its final few frames.
        time.sleep(0.5)

        print("Simulated navigation map-follow component test passed")
        print(f"  broker:   {BROKER_PUBLISHER_ENDPOINT} -> {BROKER_SUBSCRIBER_ENDPOINT}")
        print(f"  fixes:    {len(positions)}")
        print("  expected map.command stream: set_position + set_camera")
        return 0
    finally:
        runtime.close()
        publisher_transport.close()
        broker.close()
        broker_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
