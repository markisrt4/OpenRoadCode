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
from messaging.message_dispatcher import MessageDispatcher
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
            RouteManeuver("Head east", "Head east", 0.31, 45.0, 0, 1),
            RouteManeuver("Turn left", "Turn left", 0.41, 60.0, 1, 2),
            RouteManeuver("Turn right", "Turn right", 0.31, 45.0, 2, 3),
        ),
    )


def _positions() -> tuple[GeoPoint, ...]:
    return (
        GeoPoint(42.8028, -83.0127),
        GeoPoint(42.8028, -83.0097),
        GeoPoint(42.8028, -83.0067),
        GeoPoint(42.8058, -83.0067),
        # Leave the route far enough to trip the 0.05-mile threshold.
        GeoPoint(42.8058, -83.0054),
        # Move closer, but remain inside the hysteresis band (> 0.03 mile).
        GeoPoint(42.8058, -83.0059),
        # Rejoin inside the 0.03-mile recovery threshold.
        GeoPoint(42.8058, -83.0064),
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
        RouteGuidanceController(
            _route(),
            off_route_threshold_miles=0.05,
            on_route_threshold_miles=0.03,
        ),
        guidance_publisher,
    )
    received = []

    def on_guidance(message) -> None:
        received.append(message)
        data = message.data
        distance = (
            "--"
            if data.distance_to_maneuver_m is None
            else f"{data.distance_to_maneuver_m:6.1f} m"
        )
        status = "ARRIVED" if data.route_complete else (data.instruction or "--")
        route_status = "OFF" if data.off_route else "ON "
        print(f"{route_status} ROUTE  {status:12}  next={distance}")

    observer = MessageDispatcher(ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT))
    observer.register(
        ROUTE_GUIDANCE_STATE_TOPIC,
        decode_route_guidance_state,
        on_guidance,
    )

    positions = _positions()

    try:
        runtime.start()
        observer.start()
        time.sleep(0.3)

        for point in positions:
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
        while len(received) < len(positions) and time.monotonic() < deadline:
            time.sleep(0.02)

        if len(received) < len(positions):
            raise RuntimeError(
                f"Expected {len(positions)} guidance states, received {len(received)}"
            )

        states = [item.data for item in received]
        if states[0].instruction != "Head east":
            raise RuntimeError("Initial maneuver was not Head east")
        if not any(item.instruction == "Turn left" for item in states):
            raise RuntimeError("Guidance never advanced to Turn left")
        if not any(item.instruction == "Turn right" for item in states):
            raise RuntimeError("Guidance never advanced to Turn right")

        excursion = states[4:7]
        if [item.off_route for item in excursion] != [True, True, False]:
            raise RuntimeError(
                "Expected off-route excursion True -> True -> False, got "
                f"{[item.off_route for item in excursion]!r}"
            )

        if not states[-1].route_complete:
            raise RuntimeError("Final guidance state did not report arrival")

        print("Route guidance component test passed")
        print(f"  position fixes:   {len(positions)}")
        print(f"  guidance states:  {len(received)}")
        print("  maneuvers:        Head east -> Turn left -> Turn right -> ARRIVED")
        print("  off-route:        ON -> OFF -> hysteresis hold -> ON")
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
