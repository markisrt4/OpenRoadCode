# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import pytest

from controllers.route_guidance import RouteGuidanceState
from controllers.route_planning.route_planning_types import RouteManeuver
from messaging.contracts.route_guidance import (
    decode_route_guidance_state,
    encode_route_guidance_state,
    validate_route_guidance_state,
)


def _state() -> RouteGuidanceState:
    return RouteGuidanceState(
        distance_along_route_miles=1.0,
        distance_remaining_miles=2.0,
        distance_from_route_miles=0.01,
        current_maneuver_index=1,
        current_maneuver=RouteManeuver(
            instruction="Turn left",
            verbal_instruction="Turn left onto Main Street",
            distance_miles=0.5,
            duration_seconds=60.0,
            begin_shape_index=2,
            end_shape_index=5,
        ),
        distance_to_maneuver_miles=0.25,
        off_route=False,
        route_complete=False,
    )


def test_encode_uses_si_units_and_maneuver_text() -> None:
    payload = encode_route_guidance_state(_state())

    assert payload["version"] == 1
    assert payload["source"] == "route_guidance"
    assert payload["data"]["distance_along_route_m"] == pytest.approx(1609.344)
    assert payload["data"]["distance_remaining_m"] == pytest.approx(3218.688)
    assert payload["data"]["distance_to_maneuver_m"] == pytest.approx(402.336)
    assert payload["data"]["instruction"] == "Turn left"
    assert payload["data"]["verbal_instruction"] == "Turn left onto Main Street"


def test_decode_returns_typed_message() -> None:
    message = decode_route_guidance_state(encode_route_guidance_state(_state()))

    assert message.data.current_maneuver_index == 1
    assert message.data.instruction == "Turn left"
    assert not message.data.off_route
    assert not message.data.route_complete


def test_no_maneuver_encodes_nullable_fields() -> None:
    state = RouteGuidanceState(
        distance_along_route_miles=0.0,
        distance_remaining_miles=0.0,
        distance_from_route_miles=0.0,
        current_maneuver_index=None,
        current_maneuver=None,
        distance_to_maneuver_miles=None,
        off_route=False,
        route_complete=True,
    )

    payload = encode_route_guidance_state(state)

    assert payload["data"]["current_maneuver_index"] is None
    assert payload["data"]["instruction"] is None
    assert payload["data"]["verbal_instruction"] is None
    assert payload["data"]["distance_to_maneuver_m"] is None


def test_validator_rejects_negative_distance() -> None:
    payload = encode_route_guidance_state(_state())
    payload["data"]["distance_remaining_m"] = -1.0

    with pytest.raises(ValueError):
        validate_route_guidance_state(payload)
