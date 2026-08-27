# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import threading
import time

from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest
from services.navigation.navigation_command_client import NavigationCommandClient
from services.navigation.navigation_command_service import (
    NavigationCommandResult,
    NavigationCommandService,
)
from services.navigation.zeromq_navigation_command_server import ZeroMqNavigationCommandServer


class _NavigationController:
    pass


class _RoutePlanner:
    def calculate_route(self, request):
        from controllers.route_planning.route_planning_types import RouteManeuver, RouteResult
        return RouteResult(
            distance_miles=12.5,
            duration_seconds=900.0,
            shape=(request.origin, request.destination),
            maneuvers=(
                RouteManeuver(
                    instruction="Continue to destination",
                    verbal_instruction=None,
                    distance_miles=12.5,
                    duration_seconds=900.0,
                    begin_shape_index=0,
                    end_shape_index=1,
                ),
            ),
        )


def test_calculate_route_round_trip() -> None:
    endpoint = "tcp://127.0.0.1:15661"
    service = NavigationCommandService(
        _NavigationController(),
        route_planning_controller=_RoutePlanner(),
    )
    server = ZeroMqNavigationCommandServer(service, endpoint)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 2.0
    while not server.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("server did not start")
        time.sleep(0.01)

    try:
        client = NavigationCommandClient(endpoint, timeout_ms=1000)
        request = RouteRequest(
            origin=GeoPoint(42.8028, -83.0127),
            destination=GeoPoint(42.3314, -83.0458),
        )
        route = client.calculate_route(request)
        assert route.distance_miles == 12.5
        assert route.duration_seconds == 900.0
        assert route.shape == (request.origin, request.destination)
        assert route.maneuvers[0].instruction == "Continue to destination"
    finally:
        server.close()
        thread.join(timeout=1.0)
