# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed public route-guidance message."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RouteGuidanceStateData:
    distance_along_route_m: float
    distance_remaining_m: float
    distance_from_route_m: float
    current_maneuver_index: int | None
    instruction: str | None
    verbal_instruction: str | None
    distance_to_maneuver_m: float | None
    off_route: bool
    route_complete: bool


@dataclass(frozen=True, slots=True)
class RouteGuidanceStateMessage:
    version: int
    source: str
    data: RouteGuidanceStateData
