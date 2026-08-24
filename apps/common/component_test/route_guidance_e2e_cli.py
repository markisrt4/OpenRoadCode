# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise simulated positions through the real bus into route guidance."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from apps.common.route_guidance_runtime import RouteGuidanceRuntime
from controllers.navigation.navigation_state import PositionState
from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
)
from messaging.contracts.navigation import PositionStatePublisher
from messaging.contracts.route_guidance import (
    ROUTE_GUIDANCE_STATE_TOPIC,
    RouteGuidanceStatePublisher,
    decode_route_guidance_state,
)
from messaging.zeromq.broker import ZeroMqBroker
from messaging.zeromq.publisher import ZeroMqPublisher
from messaging.zeromq.subscriber import ZeroMqSubscriber

BROKER_PUBLISHER_ENDPOINT = "tcp://127.0.0.1:17556"
BROKER_SUBSCRIBER_ENDPOINT = "tcp://127.0.0.1:17557"


def _route() -> RouteResult:
    shape = (
        GeoPoint(42.8028, -83.0127),
        GeoPoint(42.8028, -83.0067),
        GeoPoint(42.8088, -83.0067),
        GeoPoint(42.8088, -83.0007),
    )
    return RouteResult(
        distance_miles=1.25,
        duration_seconds=180.0,
        shape=shape,
        maneuvers=(
            RouteManeuver(
                instruction="Head east",
                verbal_instruction="Head east",
                distance_miles=0.31,
                duration_seconds=45.0,
                begin_shape_index=0,
                end_shape_index=1,
            ),
            RouteManeuver(
                instruction="Turn left",
                verbal_instruction="Turn left",
                distance_miles=0.41,
                duration_seconds=60.0,
                begin_shape_index=1,
                end_shape_index=2,
            ),
            RouteManeuver(
                instruction="Turn right",
                verbal_instruction="Turn right",
                distance_miles=0.31,
                duration_seconds=45.0,
                begin_shape_index=2,
                end_shape_index=3,
            ),
        ),
    )


def _positions() -> tuple[GeoPoint, ...]:
    return (
        GeoPoint(42.8028, -83.0127),
        GeoPoint(42.8028, -83.0097),
        GeoPoint(42.8028, -83.0067),
        GeoPoint(42.8058, -83.0067),
        GeoPoint(42.8088, -83.0067),
        GeoPoint(42.8088, -83.0037),
        GeoPoint(42.8088, -83.0007),
    )


def _wait_for_broker(broker: ZeroMqBroker) -> None:
    deadline = time.monotonic() + 2.0
    while not broker.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("ZeroMQ broker did not start")
        time.sleep(0.01)


def main() -> int:
    broker = ZeroMqBroker(BROKER_PUBLISHER_ENDPOINT, BROKER_SUBSCRIBER_ENDPOINT)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()
    _wait_for_broker(broker)

    position_transport = ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)
    guidance_transport = ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)
    position_publisher = PositionStatePublisher(position_transport)
    guidance_publisher = RouteGuidanceStatePublisher(guidance_transport)
    runtime = RouteGuidanceRuntime(
        ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT),
        RouteGuidanceController(_route()),
        guidance_publisher,
    )
    observer = ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT)
    received = []

    def on_guidance(_topic: str, payload: dict[str, object]) -> None:
        message = decode_route_guidance_state(payload)
        received.append(message)
        data = message.data
        distance = (
            "--"
            if data.distance_to_maneuver_m is None
            else f"{data.distance_to_maneuver_m:6.1f} m"
        )
        status = "ARRIVED" if data.route_complete else (data.instruction or "--")
        print(f"{status:12}  next={distance}  off_route={data.off_route}")

    observer.subscribe(ROUTE_GUIDANCE_STATE_TOPIC, on_guidance)

    try:
        runtime.start()
        observer.start()
        time.sleep(0.3)

        for point in _positions():
            position_publisher.publish(
                PositionState(
                    received_at=datetime.now(timezone.utc),
                    latitude_deg=point.latitude,
                    longitude_deg=point.longitude,
                    speed_mps=13.4,
                    course_deg=0.0,
                    fix_mode=3,
                    source="simulation",
                )
            )
            time.sleep(0.2)

        deadline = time.monotonic() + 2.0
        while len(received) < len(_positions()) and time.monotonic() < deadline:
            time.sleep(0.02)

        if len(received) < len(_positions()):
            raise RuntimeError(
                f"Expected {len(_positions())} guidance states, received {len(received)}"
            )
        if received[0].data.instruction != "Head east":
            raise RuntimeError("Initial maneuver was not Head east")
        if not any(item.data.instruction == "Turn left" for item in received):
            raise RuntimeError("Guidance never advanced to Turn left")
        if not any(item.data.instruction == "Turn right" for item in received):
            raise RuntimeError("Guidance never advanced to Turn right")
        if not received[-1].data.route_complete:
            raise RuntimeError("Final guidance state did not report arrival")

        print("Route guidance component test passed")
        print(f"  position fixes:   {len(_positions())}")
        print(f"  guidance states:  {len(received)}")
        print("  transitions:      Head east -> Turn left -> Turn right -> ARRIVED")
        return 0
    finally:
        runtime.close()
        observer.close()
        position_transport.close()
        guidance_transport.close()
        broker.close()
        broker_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
