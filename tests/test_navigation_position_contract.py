# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
from datetime import datetime, timezone

import pytest

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import decode_position_state, encode_position_state, validate_position_state


def sample_state(**overrides):
    values = dict(
        received_at=datetime(2026, 8, 21, 18, 30, 0, 123456, tzinfo=timezone.utc),
        latitude_deg=42.8028,
        longitude_deg=-83.0127,
        altitude_m=250.5,
        speed_mps=13.4,
        course_deg=90.0,
        fix_mode=3,
        satellites_visible=14,
        satellites_used=10,
        accuracy_m=2.5,
        source="simulator",
        is_cached=False,
    )
    values.update(overrides)
    return PositionState(**values)


def test_encode_position_state_uses_strict_si_and_decodes():
    payload = encode_position_state(sample_state())
    data = payload["data"]
    assert data["latitude_rad"] == pytest.approx(math.radians(42.8028))
    assert data["longitude_rad"] == pytest.approx(math.radians(-83.0127))
    assert data["course_rad"] == pytest.approx(math.pi / 2)
    assert data["altitude_m"] == 250.5
    assert data["speed_m_s"] == 13.4
    assert payload["timestamp"]["nanoseconds"] == 123456000

    message = decode_position_state(payload)
    assert message.source == "simulator"
    assert message.data.fix_mode == 3
    assert message.data.satellites_used == 10


def test_position_contract_preserves_null_fields():
    payload = encode_position_state(sample_state(
        latitude_deg=None,
        longitude_deg=None,
        altitude_m=None,
        speed_mps=None,
        course_deg=None,
        fix_mode=None,
        satellites_visible=None,
        satellites_used=None,
        accuracy_m=None,
    ))
    for name, value in payload["data"].items():
        if name != "is_cached":
            assert value is None


def test_position_validator_rejects_invalid_latitude():
    payload = encode_position_state(sample_state())
    payload["data"]["latitude_rad"] = math.pi
    with pytest.raises(ValueError):
        validate_position_state(payload)


def test_position_validator_rejects_satellite_inconsistency():
    payload = encode_position_state(sample_state())
    payload["data"]["satellites_used"] = 15
    with pytest.raises(ValueError):
        validate_position_state(payload)


def test_position_validator_rejects_unknown_fields():
    payload = encode_position_state(sample_state())
    payload["data"]["mystery"] = 42
    with pytest.raises(ValueError):
        validate_position_state(payload)
