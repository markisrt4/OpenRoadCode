# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public data types for an active navigation session."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteResult,
    TravelMode,
)


@dataclass(frozen=True, slots=True)
class NavigationSessionState:
    """Current route request context owned by a navigation session."""

    destination: GeoPoint
    travel_mode: TravelMode
    route: RouteResult
