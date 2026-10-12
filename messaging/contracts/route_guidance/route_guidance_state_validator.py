# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public route-guidance state contract."""

from collections.abc import Mapping
from typing import Any
from ui.navigation.route_types import RouteTurn

SCHEMA_VERSION = 1


def validate_route_guidance_state(payload: Mapping[str, Any]) -> None:
    if payload.get("version") != SCHEMA_VERSION:
        raise ValueError("unsupported route guidance schema version")
    if not isinstance(payload.get("source"), str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError("data must be an object")

    required = {
        "distance_along_route_m",
        "distance_remaining_m",
        "distance_from_route_m",
        "current_maneuver_index",
        "instruction",
        "verbal_instruction",
        "distance_to_maneuver_m",
        "off_route",
        "route_complete",
    }
    if not required <= set(data) or set(data) - required - {"turn", "road_name"}:
        raise ValueError("route guidance data fields do not match schema")
    if "turn" in data and (not isinstance(data["turn"], str)
                           or data["turn"] not in {turn.value for turn in RouteTurn}):
        raise ValueError("turn must be a supported maneuver direction")
    if data.get("road_name") is not None and not isinstance(data["road_name"], str):
        raise ValueError("road_name must be null or a string")

    for name in (
        "distance_along_route_m",
        "distance_remaining_m",
        "distance_from_route_m",
    ):
        if not isinstance(data[name], (int, float)) or isinstance(data[name], bool) or data[name] < 0:
            raise ValueError(f"{name} must be a non-negative number")

    optional_distance = data["distance_to_maneuver_m"]
    if optional_distance is not None and (
        not isinstance(optional_distance, (int, float))
        or isinstance(optional_distance, bool)
        or optional_distance < 0
    ):
        raise ValueError("distance_to_maneuver_m must be null or a non-negative number")

    maneuver_index = data["current_maneuver_index"]
    if maneuver_index is not None and (
        not isinstance(maneuver_index, int)
        or isinstance(maneuver_index, bool)
        or maneuver_index < 0
    ):
        raise ValueError("current_maneuver_index must be null or a non-negative integer")

    for name in ("instruction", "verbal_instruction"):
        if data[name] is not None and not isinstance(data[name], str):
            raise ValueError(f"{name} must be null or a string")

    for name in ("off_route", "route_complete"):
        if not isinstance(data[name], bool):
            raise ValueError(f"{name} must be boolean")
