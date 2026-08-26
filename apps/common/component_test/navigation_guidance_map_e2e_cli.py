# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise simulated positions through map follow and route guidance together."""

from __future__ import annotations

import argparse
import threading
import time
from datetime import datetime, timezone

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from apps.common.route_guidance_runtime import RouteGuidanceRuntime
from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import PositionState
from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_map_presenter import present_route
from controllers.route_planning.route_planning_types import GeoPoint, RouteManeuver, RouteResult
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
from protocols.map_renderer.map_renderer_client import MapRendererClient

BROKER_PUBLISHER_ENDPOINT = "tcp://127.0.0.1:18556"
BROKER_SUBSCRIBER_ENDPOINT = "tcp://127.0.0.1:18557"
DEFAULT_RENDERER_ENDPOINT = "ipc:///tmp/openroadcode-map-renderer"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish simulated navigation fixes through the real ZeroMQ bus, "
            "drive the real map-follow runtime, and derive route guidance at "
            "the same time."
        )
    )
    parser.add_argument(
        "--renderer-endpoint",
        default=DEFAULT_RENDERER_ENDPOINT,
        help="ZeroMQ endpoint of an already-running map renderer",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.35,
        help="Seconds between simulated position fixes",
    )
    return parser.parse_args()


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


def _positions() -> tuple[tuple[GeoPoint, float], ...]:
    return (
        (GeoPoint(42.8028, -83.0127), 90.0),
        (GeoPoint(42.8028, -83.0112), 90.0),
        (GeoPoint(42.8028, -83.0097), 90.0),
        (GeoPoint(42.8028, -83.0082), 90.0),
        (GeoPoint(42.8028, -83.0067), 0.0),
        (GeoPoint(42.8043, -83.0067), 0.0),
        (GeoPoint(42.8058, -83.0067), 0.0),
        # Deliberate excursion to exercise off-route detection.
        (GeoPoint(42.8058, -83.0054), 270.0),
        # Hysteresis hold: closer, but not yet within the recovery threshold.
        (GeoPoint(42.8058, -83.0059), 270.0),
        # Rejoin the route.
        (GeoPoint(42.8058, -83.0064), 270.0),
        (GeoPoint(42.8073, -83.0067), 0.0),
        (GeoPoint(42.8088, -83.0067), 90.0),
        (GeoPoint(42.8088, -83.0052), 90.0),
        (GeoPoint(42.8088, -83.0037), 90.0),
        (GeoPoint(42.8088, -83.0022), 90.0),
        (GeoPoint(42.8088, -83.0007), 90.0),
    )


def _wait_for_broker(broker: ZeroMqBroker) -> None:
    deadline = time.monotonic() + 2.0
    while not broker.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("ZeroMQ broker did not start")
        time.sleep(0.01)


def main() -> int:
    args = _parse_args()
    if args.interval <= 0.0:
        raise ValueError("--interval must be greater than zero")

    broker = ZeroMqBroker(BROKER_PUBLISHER_ENDPOINT, BROKER_SUBSCRIBER_ENDPOINT)
    broker_thread = threading.Thread(target=broker.run, daemon=True)
    broker_thread.start()
    _wait_for_broker(broker)

    renderer = MapRendererClient(args.renderer_endpoint, timeout_ms=2000)
    route = _route()
    present_route(route, renderer)

    map_runtime = NavigationMapFollowRuntime(
        ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT),
        MapPositionAdapter(
            renderer,
            frame_rate_hz=20.0,
            correction_time_s=0.25,
            maximum_prediction_age_s=0.75,
            minimum_camera_interval_s=0.1,
        ),
    )

    guidance_transport = ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)
    guidance_runtime = RouteGuidanceRuntime(
        ZeroMqSubscriber(BROKER_SUBSCRIBER_ENDPOINT),
        RouteGuidanceController(
            route,
            off_route_threshold_miles=0.05,
            on_route_threshold_miles=0.03,
        ),
        RouteGuidanceStatePublisher(guidance_transport),
    )

    position_transport = ZeroMqPublisher(BROKER_PUBLISHER_ENDPOINT)
    position_publisher = PositionStatePublisher(position_transport)
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
        map_runtime.start()
        guidance_runtime.start()
        observer.start()
        time.sleep(0.3)

        # Help PUB/SUB slow joiners see the initial fix.
        first_point, first_course = positions[0]
        first_state = PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=first_point.latitude,
            longitude_deg=first_point.longitude,
            speed_mps=13.4,
            course_deg=first_course,
            fix_mode=3,
            source="simulation",
        )
        position_publisher.publish(first_state)
        time.sleep(0.1)

        for point, course in positions:
            state = PositionState(
                received_at=datetime.now(timezone.utc),
                latitude_deg=point.latitude,
                longitude_deg=point.longitude,
                speed_mps=13.4,
                course_deg=course,
                fix_mode=3,
                source="simulation",
            )
            position_publisher.publish(state)
            print(
                "published: "
                f"lat={point.latitude:.6f} "
                f"lon={point.longitude:.6f} "
                f"course={course:.1f}°"
            )
            time.sleep(args.interval)

        deadline = time.monotonic() + 2.0
        while len(received) < len(positions) and time.monotonic() < deadline:
            time.sleep(0.02)

        states = [item.data for item in received]
        if not states:
            raise RuntimeError("No route-guidance states were received")
        if not any(item.instruction == "Turn left" for item in states):
            raise RuntimeError("Guidance never advanced to Turn left")
        if not any(item.instruction == "Turn right" for item in states):
            raise RuntimeError("Guidance never advanced to Turn right")
        if not any(item.off_route for item in states):
            raise RuntimeError("Guidance never reported the simulated off-route excursion")
        if not states[-1].route_complete:
            raise RuntimeError("Final guidance state did not report arrival")

        time.sleep(0.5)
        print("Combined navigation guidance/map-follow component test passed")
        print(f"  renderer:         {args.renderer_endpoint}")
        print(f"  position fixes:   {len(positions)}")
        print(f"  guidance states:  {len(received)}")
        print("  maneuvers:        Head east -> Turn left -> Turn right -> ARRIVED")
        print("  map:              route + moving position + camera follow")
        print("  off-route:        excursion + hysteresis recovery")
        return 0
    finally:
        observer.close()
        guidance_runtime.close()
        map_runtime.close()
        position_transport.close()
        guidance_transport.close()
        broker.close()
        broker_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
