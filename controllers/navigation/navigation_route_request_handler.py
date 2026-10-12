# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Route-request adapter from UI contracts to the navigation command service."""

from __future__ import annotations

import math
from collections.abc import Callable

from controllers.route_planning.route_planning_types import GeoPoint as RouteGeoPoint
from controllers.route_planning.route_planning_types import RouteResult
from controllers.route_planning.route_planning_types import TravelMode as RouteTravelMode
from controllers.route_planning.route_map_presenter import present_route
from protocols.map_renderer.map_renderer_client import MapRendererClient
from services.navigation.navigation_command_client import NavigationCommandClient
from ui.navigation import GeoPoint, RouteRequestHandlerIf, RouteSimulationRequestHandlerIf
from ui.navigation.route_types import TravelMode


class NavigationRouteRequestHandler(RouteRequestHandlerIf, RouteSimulationRequestHandlerIf):
    """Send semantic UI route requests to the navigation service."""

    def __init__(
        self,
        client: NavigationCommandClient | None = None,
        map_renderer: MapRendererClient | None = None,
    ) -> None:
        self._client = client or NavigationCommandClient()
        self._map_renderer = map_renderer or MapRendererClient()
        self._active_route: RouteResult | None = None
        self._route_observers: list[Callable[[RouteResult | None], None]] = []

    @property
    def supported_travel_modes(self) -> frozenset[TravelMode]:
        """Expose only modes understood by the navigation command service."""
        return frozenset((TravelMode.AUTO, TravelMode.BICYCLE, TravelMode.PEDESTRIAN))

    @property
    def active_route(self) -> RouteResult | None:
        """Return the most recently started route, or None after cancellation."""
        return self._active_route

    def observe_route(self, observer: Callable[[RouteResult | None], None]) -> None:
        """Receive successful route starts and cancellation events."""
        self._route_observers.append(observer)

    def request_start_route(
        self,
        destination: GeoPoint,
        travel_mode: TravelMode,
    ) -> None:
        if travel_mode not in self.supported_travel_modes:
            raise ValueError(f"Unsupported route travel mode: {travel_mode.name}")
        route = self._client.start_route(
            RouteGeoPoint(
                latitude=math.degrees(destination.latitude_rad),
                longitude=math.degrees(destination.longitude_rad),
            ),
            travel_mode=RouteTravelMode[travel_mode.name],
        )
        present_route(route, self._map_renderer)
        self._active_route = route
        for observer in tuple(self._route_observers):
            observer(route)

    def request_cancel_route(self) -> None:
        self._client.cancel_route()
        self._active_route = None
        for observer in tuple(self._route_observers):
            observer(None)
        self._map_renderer.set_route(
            {"type": "FeatureCollection", "features": []}
        )

    def request_start_route_simulation(self, *, time_scale: float = 60.0) -> None:
        self._client.simulate_active_route(time_scale=time_scale)

    def request_stop_route_simulation(self) -> None:
        self._client.stop_route_simulation()

    def close(self) -> None:
        self._map_renderer.close()
