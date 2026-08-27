# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public data types for route guidance."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.route_planning.route_planning_types import RouteManeuver


@dataclass(frozen=True, slots=True)
class RouteGuidanceState:
    """Guidance state for one observed vehicle position."""

    distance_along_route_miles: float
    distance_remaining_miles: float
    distance_from_route_miles: float
    current_maneuver_index: int | None
    current_maneuver: RouteManeuver | None
    distance_to_maneuver_miles: float | None
    off_route: bool
    route_complete: bool
