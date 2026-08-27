# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode the public route-guidance state contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from controllers.route_guidance import RouteGuidanceState

from .route_guidance_state_message import (
    RouteGuidanceStateData,
    RouteGuidanceStateMessage,
)
from .route_guidance_state_validator import (
    SCHEMA_VERSION,
    validate_route_guidance_state,
)

_MILES_TO_METERS = 1609.344


def encode_route_guidance_state(
    state: RouteGuidanceState,
    *,
    source: str = "route_guidance",
) -> dict[str, Any]:
    maneuver = state.current_maneuver
    payload = {
        "version": SCHEMA_VERSION,
        "source": source,
        "data": {
            "distance_along_route_m": state.distance_along_route_miles * _MILES_TO_METERS,
            "distance_remaining_m": state.distance_remaining_miles * _MILES_TO_METERS,
            "distance_from_route_m": state.distance_from_route_miles * _MILES_TO_METERS,
            "current_maneuver_index": state.current_maneuver_index,
            "instruction": None if maneuver is None else maneuver.instruction,
            "verbal_instruction": None if maneuver is None else maneuver.verbal_instruction,
            "distance_to_maneuver_m": (
                None
                if state.distance_to_maneuver_miles is None
                else state.distance_to_maneuver_miles * _MILES_TO_METERS
            ),
            "off_route": state.off_route,
            "route_complete": state.route_complete,
        },
    }
    validate_route_guidance_state(payload)
    return payload


def decode_route_guidance_state(
    payload: Mapping[str, Any],
) -> RouteGuidanceStateMessage:
    validate_route_guidance_state(payload)
    data = payload["data"]
    return RouteGuidanceStateMessage(
        version=payload["version"],
        source=payload["source"],
        data=RouteGuidanceStateData(
            **{
                name: data[name]
                for name in RouteGuidanceStateData.__dataclass_fields__
            }
        ),
    )
