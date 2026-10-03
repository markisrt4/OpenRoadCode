# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolve textual destinations and submit route-planning requests."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.navigation.geocoding import GeocodedLocation, GeocoderIf
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteRequest,
    RouteResult,
    TravelMode,
)


@dataclass(frozen=True, slots=True)
class DestinationRoute:
    """Resolved destination together with the calculated route."""

    destination: GeocodedLocation
    route: RouteResult


class DestinationController:
    """Bridge human-readable destinations to the route planner."""

    def __init__(
        self,
        geocoder: GeocoderIf,
        route_planner: RoutePlanningControllerIf,
    ) -> None:
        self._geocoder = geocoder
        self._route_planner = route_planner

    def route_to(
        self,
        origin: GeoPoint,
        destination_text: str,
        travel_mode: TravelMode = TravelMode.AUTO,
    ) -> DestinationRoute | None:
        """Geocode destination_text and calculate a route from origin."""
        if not destination_text.strip():
            raise ValueError("destination_text must not be empty")

        destination = self._geocoder.geocode(destination_text)
        if destination is None:
            return None

        route = self._route_planner.calculate_route(
            RouteRequest(
                origin=origin,
                destination=GeoPoint(
                    latitude=destination.latitude_deg,
                    longitude=destination.longitude_deg,
                ),
                travel_mode=travel_mode,
            )
        )
        return DestinationRoute(destination=destination, route=route)
