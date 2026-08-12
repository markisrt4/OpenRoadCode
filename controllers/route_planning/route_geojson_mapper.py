# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Convert route-planning types to GeoJSON."""

from __future__ import annotations

from typing import Any

from controllers.route_planning.route_planning_types import (
    RouteResult,
)


def route_to_geojson(
    route: RouteResult,
) -> dict[str, Any]:
    """Convert a calculated route to a GeoJSON feature.

    @param route Route whose decoded shape should become a LineString.
    @return GeoJSON Feature containing the route geometry and summary.
    """

    coordinates = [
        [
            point.longitude,
            point.latitude,
        ]
        for point in route.shape
    ]

    return {
        "type": "Feature",
        "properties": {
            "distance_miles": route.distance_miles,
            "duration_seconds": route.duration_seconds,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
    }
