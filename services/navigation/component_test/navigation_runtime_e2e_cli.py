# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise active-route lifecycle through the production NavigationRuntime."""

from __future__ import annotations

import threading
import time
from datetime import datetime

import zmq

from controllers.navigation.navigation_state import NavigationState, PositionState
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
    TravelMode,
)
from hardware_io.imu import Vector3
from services.navigation.navigation_command_service import (
    CANCEL_ROUTE_COMMAND,
    START_ROUTE_COMMAND,
)
from services.navigation.navigation_runtime import NavigationRuntime

COMMAND_ENDPOINT = "tcp://127.0.0.1:18560"
OFF_ROUTE_POSITION = GeoPoint(42.0100, -83.0000)
DESTINATION = GeoPoint(42.0000, -82.9900)


class _DiscardingPublisher:
    def publish(self, topic: str, payload: bytes) -> None:
        pass


class _FixedNavigationController:
    """Continuously report one valid GPS position for runtime guidance updates."""

    def __init__(self, position: GeoPoint) -> None:
        self._position = position
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def calibrate_stationary(self, *, sample_count: int = 100, sample_interval_s: float = 0.01) -> None:
        pass

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        pass

    def read_state(self) -> NavigationState:
        zero = Vector3(0.0, 0.0, 0.0)
        return NavigationState(
            timestamp=datetime.now(),
            heading_deg=90.0,
            pitch_deg=0.0,
            roll_deg=0.0,
            acceleration_mps2=zero,
            linear_acceleration_mps2=zero,
            angular_velocity_rad_s=zero,
            gps=PositionState(
                latitude_deg=self._position.latitude,
                longitude_deg=self._position.longitude,
                speed_mps=10.0,
                course_deg=90.0,
                fix_mode=3,
                source="component-test",
            ),
        )


class _SequencedRoutePlanner(RoutePlanningControllerIf):
    """Return an initial route, then a route based on the reroute origin."""

    def __init__(self) -> None:
        self.requests: list[RouteRequest] = []

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    def calculate_route(self, request: RouteRequest) -> RouteResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            shape = (
                GeoPoint(42.0000, -83.0000),
                DESTINATION,
            )
        else:
            shape = (
                request.origin,
                request.destination,
            )
        return RouteResult(
            distance_miles=0.5,
            duration_seconds=60.0,
            shape=shape,
            maneuvers=(
                RouteManeuver(
                    instruction="Continue",
                    verbal_instruction="Continue",
                    distance_miles=0.5,
                    duration_seconds=60.0,
                    begin_shape_index=0,
                    end_shape_index=1,
                ),
            ),
        )


def _request(command: str, arguments: dict | None = None) -> dict:
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.SNDTIMEO, 2000)
    socket.setsockopt(zmq.RCVTIMEO, 2000)
    try:
        socket.connect(COMMAND_ENDPOINT)
        socket.send_json({"command": command, "arguments": arguments or {}})
        return socket.recv_json()
    finally:
        socket.close(linger=0)
        context.term()


def _wait_until(predicate, message: str, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not predicate():
        if time.monotonic() >= deadline:
            raise RuntimeError(message)
        time.sleep(0.02)


def main() -> int:
    controller = _FixedNavigationController(OFF_ROUTE_POSITION)
    planner = _SequencedRoutePlanner()
    runtime = NavigationRuntime(
        controller,
        _DiscardingPublisher(),
        source="runtime-component-test",
        rate_hz=20.0,
        command_endpoint=COMMAND_ENDPOINT,
        route_planning_controller=planner,
    )
    runtime_thread = threading.Thread(
        target=runtime.run,
        name="navigation-runtime-component-test",
        daemon=True,
    )
    runtime_thread.start()

    try:
        _wait_until(
            lambda: runtime._command_server.is_running,
            "NavigationRuntime command server did not start",
        )

        start_response = _request(
            START_ROUTE_COMMAND,
            {
                "origin": {"latitude": 42.0000, "longitude": -83.0000},
                "destination": {
                    "latitude": DESTINATION.latitude,
                    "longitude": DESTINATION.longitude,
                },
                "travel_mode": TravelMode.AUTO.name,
            },
        )
        if not start_response.get("ok"):
            raise RuntimeError(f"Route start failed: {start_response}")

        _wait_until(
            lambda: len(planner.requests) >= 2,
            "NavigationRuntime did not reroute after sustained off-route guidance",
        )

        reroute_request = planner.requests[1]
        if reroute_request.origin != OFF_ROUTE_POSITION:
            raise RuntimeError(
                f"Reroute did not use current GPS position: {reroute_request.origin!r}"
            )
        if reroute_request.destination != DESTINATION:
            raise RuntimeError(
                f"Reroute did not retain destination: {reroute_request.destination!r}"
            )

        session = runtime._session_controller
        if session is None or session.state is None:
            raise RuntimeError("NavigationRuntime did not retain an active route session")
        if session.state.route.shape[0] != OFF_ROUTE_POSITION:
            raise RuntimeError("Replacement route was not installed in the active session")

        cancel_response = _request(CANCEL_ROUTE_COMMAND)
        if not cancel_response.get("ok"):
            raise RuntimeError(f"Route cancel failed: {cancel_response}")
        if session.state is not None:
            raise RuntimeError("Route cancellation did not clear the active session")

        print("NavigationRuntime end-to-end component test passed")
        print("  route start:       ZeroMQ -> NavigationCommandService -> NavigationRuntime")
        print("  guidance input:    runtime GPS telemetry loop")
        print("  reroute trigger:   sustained off-route guidance")
        print("  reroute origin:    current GPS position")
        print("  route replacement: installed in active session and guidance")
        print("  route cancel:      ZeroMQ -> active session cleared")
        return 0
    finally:
        runtime.close()
        runtime_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
