# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Drive the Car UI turn-by-turn panel with deterministic route guidance."""

from __future__ import annotations

import argparse
import threading
import time

from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_planning_types import GeoPoint, RouteManeuver, RouteResult
from messaging.contracts.route_guidance import RouteGuidanceStatePublisher
from messaging.zeromq.broker import ZeroMqBroker
from messaging.zeromq.publisher import ZeroMqPublisher

PUBLISHER_ENDPOINT = "tcp://127.0.0.1:5556"
SUBSCRIBER_ENDPOINT = "tcp://127.0.0.1:5557"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish deterministic turn-by-turn guidance for Car UI testing."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.25,
        help="Seconds between simulated positions",
    )
    parser.add_argument(
        "--startup-delay",
        type=float,
        default=4.0,
        help="Seconds to wait before beginning the route",
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


def _positions() -> tuple[GeoPoint, ...]:
    return (
        GeoPoint(42.8028, -83.0127),
        GeoPoint(42.8028, -83.0112),
        GeoPoint(42.8028, -83.0097),
        GeoPoint(42.8028, -83.0082),
        GeoPoint(42.8028, -83.0067),
        GeoPoint(42.8043, -83.0067),
        GeoPoint(42.8058, -83.0067),
        # Deliberate excursion to exercise off-route presentation.
        GeoPoint(42.8058, -83.0054),
        GeoPoint(42.8058, -83.0059),
        GeoPoint(42.8058, -83.0064),
        GeoPoint(42.8073, -83.0067),
        GeoPoint(42.8088, -83.0067),
        GeoPoint(42.8088, -83.0052),
        GeoPoint(42.8088, -83.0037),
        GeoPoint(42.8088, -83.0022),
        GeoPoint(42.8088, -83.0007),
    )


def _start_broker(
    broker: ZeroMqBroker,
) -> tuple[threading.Thread, list[BaseException]]:
    errors: list[BaseException] = []

    def run_broker() -> None:
        try:
            broker.run()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run_broker, daemon=True)
    thread.start()
    return thread, errors


def _wait_for_broker(
    broker: ZeroMqBroker,
    broker_thread: threading.Thread,
    errors: list[BaseException],
) -> None:
    deadline = time.monotonic() + 2.0
    while not broker.is_running:
        if errors:
            raise RuntimeError(str(errors[0])) from None
        if not broker_thread.is_alive():
            raise RuntimeError("broker exited before becoming ready")
        if time.monotonic() >= deadline:
            raise RuntimeError("broker did not become ready within 2 seconds")
        time.sleep(0.01)


def main() -> int:
    args = _parse_args()
    if args.interval <= 0.0:
        print("Error: --interval must be greater than zero")
        return 2
    if args.startup_delay < 0.0:
        print("Error: --startup-delay must not be negative")
        return 2

    broker = ZeroMqBroker(PUBLISHER_ENDPOINT, SUBSCRIBER_ENDPOINT)
    broker_thread, broker_errors = _start_broker(broker)
    try:
        _wait_for_broker(broker, broker_thread, broker_errors)
    except RuntimeError as error:
        broker.close()
        broker_thread.join(timeout=1.0)
        print("Unable to start the Car UI guidance demo broker.")
        print(f"  publisher endpoint:  {PUBLISHER_ENDPOINT}")
        print(f"  subscriber endpoint: {SUBSCRIBER_ENDPOINT}")
        print(f"  reason:              {error}")
        print("Another OpenRoadCode broker may already be using these endpoints.")
        return 1

    transport = ZeroMqPublisher(PUBLISHER_ENDPOINT)
    publisher = RouteGuidanceStatePublisher(transport, source="car-ui-guidance-demo")
    guidance = RouteGuidanceController(
        _route(),
        off_route_threshold_miles=0.05,
        on_route_threshold_miles=0.03,
    )

    try:
        print("Car UI turn-by-turn guidance demo")
        print(f"  publisher endpoint:  {PUBLISHER_ENDPOINT}")
        print(f"  subscriber endpoint: {SUBSCRIBER_ENDPOINT}")
        print(f"  route begins in:      {args.startup_delay:g} seconds")
        print("Open the NAVIGATION panel in Car UI now.")
        time.sleep(args.startup_delay)

        # Let PUB/SUB subscriptions settle before the first visible state.
        time.sleep(0.3)
        for position in _positions():
            state = guidance.update(position)
            publisher.publish(state)
            maneuver = state.current_maneuver
            instruction = "ARRIVED" if state.route_complete else (
                "--" if maneuver is None else maneuver.instruction
            )
            distance = state.distance_to_maneuver_miles
            distance_text = "--" if distance is None else f"{distance:.2f} mi"
            route_state = "OFF ROUTE" if state.off_route else "ON ROUTE"
            print(f"{route_state:9}  {instruction:12}  next={distance_text}")
            time.sleep(args.interval)

        print("Turn-by-turn guidance demo complete")
        time.sleep(1.0)
        return 0
    except KeyboardInterrupt:
        print("\nTurn-by-turn guidance demo stopped")
        return 130
    finally:
        transport.close()
        broker.close()
        broker_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
