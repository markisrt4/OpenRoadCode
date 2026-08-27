# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command service for navigation, routing, and active-route lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Mapping

from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest, RouteResult, TravelMode

CALIBRATE_STATIONARY_COMMAND = "navigation.calibrate_stationary"
RESET_HEADING_COMMAND = "navigation.reset_heading"
CALCULATE_ROUTE_COMMAND = "navigation.route.calculate"
START_ROUTE_COMMAND = "navigation.route.start"
CANCEL_ROUTE_COMMAND = "navigation.route.cancel"

RouteStartedCallback = Callable[[RouteRequest, RouteResult], None]
RouteCancelledCallback = Callable[[], None]


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
        *,
        on_route_started: RouteStartedCallback | None = None,
        on_route_cancelled: RouteCancelledCallback | None = None,
    ) -> None:
        self._controller = controller
        self._route_planning_controller = route_planning_controller
        self._on_route_started = on_route_started
        self._on_route_cancelled = on_route_cancelled

    def execute(self, command: str, arguments: Mapping[str, Any] | None = None) -> NavigationCommandResult:
        args = dict(arguments or {})

        if command == CALIBRATE_STATIONARY_COMMAND:
            self._controller.calibrate_stationary(
                sample_count=int(args.get("sample_count", 100)),
                sample_interval_s=float(args.get("sample_interval_s", 0.01)),
            )
            return NavigationCommandResult(True, "Stationary calibration complete")

        if command == RESET_HEADING_COMMAND:
            self._controller.reset_heading(float(args.get("heading_deg", 0.0)))
            return NavigationCommandResult(True, "Heading reset complete")

        if command in {CALCULATE_ROUTE_COMMAND, START_ROUTE_COMMAND}:
            return self._route_command(args, activate=command == START_ROUTE_COMMAND)

        if command == CANCEL_ROUTE_COMMAND:
            if self._on_route_cancelled is not None:
                self._on_route_cancelled()
            return NavigationCommandResult(True, "Active route cancelled")

        return NavigationCommandResult(False, f"Unknown navigation command: {command}")

    def _route_command(self, args: Mapping[str, Any], *, activate: bool) -> NavigationCommandResult:
        if self._route_planning_controller is None:
            return NavigationCommandResult(False, "Route planning is not configured")

        try:
            request = self._parse_route_request(args)
        except (KeyError, TypeError, ValueError) as error:
            return NavigationCommandResult(False, f"Invalid route request: {error}")

        route = self._route_planning_controller.calculate_route(request)
        if activate:
            if self._on_route_started is None:
                return NavigationCommandResult(False, "Route guidance is not configured")
            self._on_route_started(request, route)

        return NavigationCommandResult(
            True,
            "Route started" if activate else "Route calculated",
            data=self._route_data(route),
        )

    @staticmethod
    def _parse_route_request(args: Mapping[str, Any]) -> RouteRequest:
        origin = args.get("origin")
        destination = args.get("destination")
        if not isinstance(origin, Mapping) or not isinstance(destination, Mapping):
            raise ValueError("origin and destination objects are required")

        travel_mode_name = str(args.get("travel_mode", "AUTO")).upper()
        try:
            travel_mode = TravelMode[travel_mode_name]
        except KeyError as error:
            raise ValueError(f"Unsupported travel mode: {travel_mode_name}") from error

        return RouteRequest(
            origin=GeoPoint(latitude=float(origin["latitude"]), longitude=float(origin["longitude"])),
            destination=GeoPoint(latitude=float(destination["latitude"]), longitude=float(destination["longitude"])),
            travel_mode=travel_mode,
        )

    @staticmethod
    def _route_data(route: RouteResult) -> Mapping[str, Any]:
        return {
            "distance_miles": route.distance_miles,
            "duration_seconds": route.duration_seconds,
            "shape": [{"latitude": point.latitude, "longitude": point.longitude} for point in route.shape],
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
        }
