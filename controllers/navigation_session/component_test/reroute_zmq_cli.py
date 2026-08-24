# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise rerouting through the real navigation ZeroMQ command transport."""

from __future__ import annotations

import threading
import time

from controllers.navigation import SimulatedNavigationController
from controllers.navigation_session import NavigationSessionController
from controllers.route_guidance import ReroutePolicy, RouteGuidanceController
from controllers.route_guidance.route_guidance_types import RouteGuidanceState
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
    TravelMode,
)
from services.navigation.navigation_command_client import NavigationCommandClient
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import ZeroMqNavigationCommandServer

COMMAND_ENDPOINT = "tcp://127.0.0.1:17560"


class _RecordingRoutePlanner(RoutePlanningControllerIf):
    """Return a deterministic replacement route and retain received requests."""

    def __init__(self, route: RouteResult) -> None:
        self._route = route
        self.requests: list[RouteRequest] = []

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    def calculate_route(self, request: RouteRequest) -> RouteResult:
        self.requests.append(request)
        return self._route


def _route(latitude_offset: float = 0.0) -> RouteResult:
    shape = (
        GeoPoint(42.0000 + latitude_offset, -83.0000),
        GeoPoint(42.0000 + latitude_offset, -82.9900),
    )
    return RouteResult(
        distance_miles=0.5,
        duration_seconds=60.0,
        shape=shape,
        maneuvers=(
            RouteManeuver(
                instruction="Continue east",
                verbal_instruction="Continue east",
                distance_miles=0.5,
                duration_seconds=60.0,
                begin_shape_index=0,
                end_shape_index=1,
            ),
        ),
    )


def _off_route_state() -> RouteGuidanceState:
    return RouteGuidanceState(
        distance_along_route_miles=0.2,
        distance_remaining_miles=0.3,
        distance_from_route_miles=0.1,
        current_maneuver_index=0,
        current_maneuver=None,
        distance_to_maneuver_miles=0.3,
        off_route=True,
        route_complete=False,
    )


def _wait_for_server(server: ZeroMqNavigationCommandServer) -> None:
    deadline = time.monotonic() + 2.0
    while not server.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("Navigation command server did not start")
        time.sleep(0.01)


def main() -> int:
    initial_route = _route()
    replacement_route = _route(latitude_offset=0.01)
    planner = _RecordingRoutePlanner(replacement_route)
    service = NavigationCommandService(
        SimulatedNavigationController(),
        route_planning_controller=planner,
    )
    server = ZeroMqNavigationCommandServer(service, COMMAND_ENDPOINT)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    _wait_for_server(server)

    client = NavigationCommandClient(COMMAND_ENDPOINT)
    guidance = RouteGuidanceController(initial_route)
    changed: list[RouteResult] = []
    session = NavigationSessionController(
        client.calculate_route,
        guidance,
        ReroutePolicy(off_route_delay_s=0.0, cooldown_s=0.0),
        on_route_changed=changed.append,
    )

    destination = GeoPoint(42.1000, -82.9000)
    original_request = RouteRequest(
        origin=GeoPoint(42.0000, -83.0000),
        destination=destination,
        travel_mode=TravelMode.AUTO,
    )
    current_position = GeoPoint(42.0200, -82.9800)

    try:
        session.start(original_request, route=initial_route)
        changed.clear()

        rerouted = session.update(current_position, _off_route_state())

        if rerouted != replacement_route:
            raise RuntimeError("Session did not install the route returned over ZeroMQ")
        if planner.requests != [
            RouteRequest(current_position, destination, TravelMode.AUTO)
        ]:
            raise RuntimeError(f"Unexpected reroute request: {planner.requests!r}")
        if session.state is None or session.state.route != replacement_route:
            raise RuntimeError("Session state did not retain the replacement route")
        if changed != [replacement_route]:
            raise RuntimeError("Route-changed callback did not receive replacement route")

        new_guidance = guidance.update(replacement_route.shape[0])
        if new_guidance.off_route:
            raise RuntimeError("Guidance controller did not switch to replacement route")

        print("Navigation reroute ZeroMQ component test passed")
        print("  trigger:          sustained off-route")
        print("  request origin:   current simulated position")
        print("  destination:      original session destination")
        print("  command path:     NavigationCommandClient -> ZeroMQ -> NavigationCommandService")
        print("  replacement:      installed in session and guidance controller")
        return 0
    finally:
        server.close()
        server_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
