# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for diagnostic vehicle-state schema validation."""

from datetime import datetime, timezone

import pytest

from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.automotive.vehicle_state_codec import encode_vehicle_state
from messaging.contracts.automotive.vehicle_state_validator import validate_vehicle_state


def _valid_payload():
    return encode_vehicle_state(
        VehicleState(timestamp=datetime.now(timezone.utc)),
        source="test-automotive",
    )


def test_schema_error_reports_missing_field() -> None:
    payload = _valid_payload()
    payload["data"].pop("transmission_gear")

    with pytest.raises(
        ValueError,
        match=r"missing=\['transmission_gear'\], unknown=\[\]",
    ):
        validate_vehicle_state(payload)


def test_schema_error_reports_unknown_field() -> None:
    payload = _valid_payload()
    payload["data"]["mystery_sensor"] = 42

    with pytest.raises(
        ValueError,
        match=r"missing=\[\], unknown=\['mystery_sensor'\]",
    ):
        validate_vehicle_state(payload)


def test_current_encoder_satisfies_current_validator() -> None:
    validate_vehicle_state(_valid_payload())
