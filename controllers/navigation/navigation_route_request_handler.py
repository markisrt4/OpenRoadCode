# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Route-request adapter from UI contracts to the navigation command service."""

from __future__ import annotations

import math
from collections.abc import Sequence

from controllers.route_planning.route_planning_types import GeoPoint as RouteGeoPoint
from controllers.route_planning.route_planning_types import TravelMode as RouteTravelMode
from services.navigation.navigation_command_client import NavigationCommandClient
from ui.navigation import GeoPoint, RouteRequestHandlerIf
from ui.navigation.route_types import TravelMode


class NavigationRouteRequestHandler(RouteRequestHandlerIf):
    """Send semantic UI route requests to the navigation service."""

    def __init__(self, client: NavigationCommandClient | None = None) -> None:
        self._client = client or NavigationCommandClient()
        self._travel_mode = TravelMode.AUTO
        self._waypoints: tuple[GeoPoint, ...] = ()

    def request_start_route(
        self,
        destination: GeoPoint,
        waypoints: Sequence[GeoPoint],
        travel_mode: TravelMode,
    ) -> None:
        if waypoints:
            raise NotImplementedError("navigation command service does not yet support waypoints")
        self._travel_mode = travel_mode
        self._client.start_route(
            RouteGeoPoint(
                latitude=math.degrees(destination.latitude_rad),
                longitude=math.degrees(destination.longitude_rad),
            ),
            travel_mode=RouteTravelMode[travel_mode.name],
        )

    def request_cancel_route(self) -> None:
        self._client.cancel_route()

    def request_add_waypoint(self, waypoint: GeoPoint) -> None:
        self._waypoints = (*self._waypoints, waypoint)

    def request_remove_waypoint(self, waypoint_index: int) -> None:
        if not 0 <= waypoint_index < len(self._waypoints):
            raise IndexError("waypoint_index out of range")
        self._waypoints = tuple(
            point for index, point in enumerate(self._waypoints) if index != waypoint_index
        )

    def request_select_alternative(self, alternative_index: int) -> None:
        raise NotImplementedError("route alternatives are not yet supported")

    def request_recalculate_route(self) -> None:
        raise NotImplementedError("explicit route recalculation is owned by the navigation session")

    def request_travel_mode(self, travel_mode: TravelMode) -> None:
        self._travel_mode = travel_mode

    def request_voice_guidance_muted(self, muted: bool) -> None:
        del muted
