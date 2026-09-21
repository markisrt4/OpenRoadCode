# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
from unittest.mock import Mock, patch

from controllers.navigation.navigation_route_request_handler import (
    NavigationRouteRequestHandler,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint as RouteGeoPoint,
    RouteResult,
)
from ui.navigation import GeoPoint
from ui.navigation.route_types import TravelMode


def test_start_route_converts_ui_point_and_presents_route() -> None:
    client = Mock()
    renderer = Mock()
    route = RouteResult(
        distance_miles=1.0,
        duration_seconds=60.0,
        shape=(RouteGeoPoint(42.8, -83.0), RouteGeoPoint(42.7, -83.1)),
        maneuvers=(),
    )
    client.start_route.return_value = route
    handler = NavigationRouteRequestHandler(client, renderer)

    destination = GeoPoint(math.radians(42.7), math.radians(-83.1))
    with patch(
        "controllers.navigation.navigation_route_request_handler.present_route"
    ) as present:
        handler.request_start_route(destination, (), TravelMode.AUTO)

    args, kwargs = client.start_route.call_args
    assert math.isclose(args[0].latitude, 42.7)
    assert math.isclose(args[0].longitude, -83.1)
    assert kwargs["travel_mode"].name == "AUTO"
    present.assert_called_once_with(route, renderer)


def test_cancel_route_clears_renderer_route() -> None:
    client = Mock()
    renderer = Mock()
    handler = NavigationRouteRequestHandler(client, renderer)

    handler.request_cancel_route()

    client.cancel_route.assert_called_once_with()
    renderer.set_route.assert_called_once_with(
        {"type": "FeatureCollection", "features": []}
    )


def test_close_closes_renderer_client() -> None:
    renderer = Mock()
    handler = NavigationRouteRequestHandler(Mock(), renderer)

    handler.close()

    renderer.close.assert_called_once_with()


def test_route_simulation_requests_delegate_to_navigation_client() -> None:
    client = Mock()
    renderer = Mock()
    handler = NavigationRouteRequestHandler(client, renderer)

    handler.request_start_route_simulation(time_scale=30.0)
    handler.request_stop_route_simulation()

    client.simulate_active_route.assert_called_once_with(time_scale=30.0)
    client.stop_route_simulation.assert_called_once_with()
