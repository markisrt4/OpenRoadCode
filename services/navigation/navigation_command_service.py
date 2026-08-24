# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation command service independent of its request transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.route_planning.route_planning_controller_if import (
    RoutePlanningControllerIf,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteRequest,
    TravelMode,
)

CALIBRATE_STATIONARY_COMMAND = "navigation.calibrate_stationary"
RESET_HEADING_COMMAND = "navigation.reset_heading"
CALCULATE_ROUTE_COMMAND = "navigation.route.calculate"


@dataclass(frozen=True, slots=True)
class NavigationCommandResult:
    """Result returned by one navigation command request."""

    ok: bool
    message: str
    data: Mapping[str, Any] | None = None


class NavigationCommandService:
    """Execute navigation commands against navigation and routing controllers."""

    def __init__(
        self,
        controller: NavigationControllerIf,
        route_planning_controller: RoutePlanningControllerIf | None = None,
    ) -> None:
        self._controller = controller
        self._route_planning_controller = route_planning_controller

    def execute(
        self,
        command: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> NavigationCommandResult:
        """Execute one named command and return a transport-neutral result."""
        args = dict(arguments or {})

        if command == CALIBRATE_STATIONARY_COMMAND:
            sample_count = int(args.get("sample_count", 100))
            sample_interval_s = float(args.get("sample_interval_s", 0.01))
            self._controller.calibrate_stationary(
                sample_count=sample_count,
                sample_interval_s=sample_interval_s,
            )
            return NavigationCommandResult(True, "Stationary calibration complete")

        if command == RESET_HEADING_COMMAND:
            heading_deg = float(args.get("heading_deg", 0.0))
            self._controller.reset_heading(heading_deg)
            return NavigationCommandResult(True, "Heading reset complete")

        if command == CALCULATE_ROUTE_COMMAND:
            return self._calculate_route(args)

        return NavigationCommandResult(False, f"Unknown navigation command: {command}")

    def _calculate_route(self, args: Mapping[str, Any]) -> NavigationCommandResult:
        if self._route_planning_controller is None:
            return NavigationCommandResult(False, "Route planning is not configured")

        origin = args.get("origin")
        destination = args.get("destination")
        if not isinstance(origin, Mapping) or not isinstance(destination, Mapping):
            return NavigationCommandResult(
                False,
                "Route calculation requires origin and destination objects",
            )

        travel_mode_name = str(args.get("travel_mode", "AUTO")).upper()
        try:
            travel_mode = TravelMode[travel_mode_name]
        except KeyError:
            return NavigationCommandResult(
                False,
                f"Unsupported travel mode: {travel_mode_name}",
            )

        try:
            request = RouteRequest(
                origin=GeoPoint(
                    latitude=float(origin["latitude"]),
                    longitude=float(origin["longitude"]),
                ),
                destination=GeoPoint(
                    latitude=float(destination["latitude"]),
                    longitude=float(destination["longitude"]),
                ),
                travel_mode=travel_mode,
            )
        except (KeyError, TypeError, ValueError) as error:
            return NavigationCommandResult(False, f"Invalid route request: {error}")

        route = self._route_planning_controller.calculate_route(request)

        return NavigationCommandResult(
            True,
            "Route calculated",
            data={
                "distance_miles": route.distance_miles,
                "duration_seconds": route.duration_seconds,
                "shape": [
                    {
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                    }
                    for point in route.shape
                ],
                "maneuvers": [
                    {
                        "instruction": maneuver.instruction,
                        "verbal_instruction": maneuver.verbal_instruction,
                        "distance_miles": maneuver.distance_miles,
                        "duration_seconds": maneuver.duration_seconds,
                        "begin_shape_index": maneuver.begin_shape_index,
                        "end_shape_index": maneuver.end_shape_index,
                    }
                    for maneuver in route.maneuvers
                ],
            },
        )
