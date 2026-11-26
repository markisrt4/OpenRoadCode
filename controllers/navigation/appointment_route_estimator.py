# SPDX-License-Identifier: MIT
"""Adapt existing offline geocoding and routing contracts for appointments."""

from math import degrees

from controllers.navigation.geocoder_if import GeocoderIf
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import GeoPoint as RoutePoint
from controllers.route_planning.route_planning_types import RouteRequest
from ui.navigation.map_ui_if import GeoPoint


def resolve_appointment_address(geocoder: GeocoderIf, location: str) -> tuple[GeoPoint, ...]:
    """Return address candidates without accepting street-level approximations.

    @param geocoder Existing geocoding contract.
    @param location Calendar location text.
    @return Candidate address coordinates.
    """
    return tuple(
        result.position for result in geocoder.geocode(location) if result.source == "address"
    )


def estimate_appointment_route(
    router: RoutePlanningControllerIf, origin: GeoPoint, destination: GeoPoint
) -> float:
    """Calculate travel duration without changing active guidance.

    @param router Independent route calculation controller.
    @param origin Current geographic position in radians.
    @param destination Appointment destination in radians.
    @return Estimated travel duration in seconds.
    """
    request = RouteRequest(
        RoutePoint(degrees(origin.latitude_rad), degrees(origin.longitude_rad)),
        RoutePoint(degrees(destination.latitude_rad), degrees(destination.longitude_rad)),
    )
    return router.calculate_route(request).duration_seconds
