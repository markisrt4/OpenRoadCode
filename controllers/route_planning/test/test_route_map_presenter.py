# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.route_planning.route_map_presenter import (
    present_route,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteResult,
)


def test_present_route() -> None:
    route = RouteResult(
        distance_miles=10.0,
        duration_seconds=600.0,
        shape=(
            GeoPoint(
                latitude=42.3500,
                longitude=-83.1000,
            ),
            GeoPoint(
                latitude=42.3314,
                longitude=-83.0458,
            ),
        ),
        maneuvers=(),
    )

    map_renderer = Mock()

    present_route(
        route=route,
        map_renderer=map_renderer,
        padding=50.0,
    )

    map_renderer.set_route.assert_called_once()

    map_renderer.fit_bounds.assert_called_once_with(
        south=42.3314,
        west=-83.1000,
        north=42.3500,
        east=-83.0458,
        padding=50.0,
    )
