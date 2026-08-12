"""Present calculated routes on the native map renderer."""

from __future__ import annotations

from controllers.route_planning.route_geojson_mapper import (
    route_to_geojson,
)
from controllers.route_planning.route_planning_types import (
    RouteResult,
)
from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
)


DEFAULT_ROUTE_PADDING = 50.0


def present_route(
    route: RouteResult,
    map_renderer: MapRendererClient,
    padding: float = DEFAULT_ROUTE_PADDING,
) -> None:
    """Display a route and fit the map camera to it.

    @param route Calculated route to display.
    @param map_renderer Client connected to the native renderer.
    @param padding Map padding applied while fitting the route bounds.
    @exception ValueError If the route has no shape points.
    """

    if not route.shape:
        raise ValueError(
            "Cannot present a route with an empty shape"
        )

    map_renderer.set_route(
        route_to_geojson(route)
    )

    south = min(
        point.latitude
        for point in route.shape
    )

    north = max(
        point.latitude
        for point in route.shape
    )

    west = min(
        point.longitude
        for point in route.shape
    )

    east = max(
        point.longitude
        for point in route.shape
    )

    map_renderer.fit_bounds(
        south=south,
        west=west,
        north=north,
        east=east,
        padding=padding,
    )
