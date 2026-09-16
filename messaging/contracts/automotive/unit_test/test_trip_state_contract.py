# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the public automotive trip-state messaging contract."""

from datetime import datetime, timezone

import pytest

from controllers.automotive import TripState, TripStatus
from messaging.contracts.automotive import (
    TRIP_STATE_TOPIC,
    decode_trip_state,
    encode_trip_state,
    validate_trip_state,
)


def test_trip_state_round_trip() -> None:
    started = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)
    state = TripState(
        status=TripStatus.ACTIVE,
        started_at=started,
        elapsed_s=60.0,
        moving_s=55.0,
        stopped_s=5.0,
        distance_m=1000.0,
        average_speed_m_s=1000.0 / 55.0,
        maximum_speed_m_s=25.0,
        boost_time_s=12.0,
        boost_distance_m=150.0,
        boost_fuel_used_m3=0.0001,
        peak_boost_pa=55000.0,
        current_latitude_deg=42.8,
        current_longitude_deg=-83.0,
    )

    payload = encode_trip_state(state, source="test", timestamp=started)
    message = decode_trip_state(payload)

    assert TRIP_STATE_TOPIC == "openroad.vehicle.trip.state"
    assert message.version == 2
    assert message.source == "test"
    assert message.data.status == "active"
    assert message.data.distance_m == pytest.approx(1000.0)
    assert message.data.current_latitude_deg == pytest.approx(42.8)
    assert message.data.boost_time_s == pytest.approx(12.0)
    assert message.data.boost_distance_m == pytest.approx(150.0)
    assert message.data.boost_fuel_used_m3 == pytest.approx(0.0001)
    assert message.data.peak_boost_pa == pytest.approx(55000.0)


def test_validator_rejects_unknown_fields() -> None:
    payload = encode_trip_state(
        TripState(),
        source="test",
        timestamp=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    payload["data"]["surprise"] = 42

    with pytest.raises(ValueError):
        validate_trip_state(payload)


def test_validator_rejects_invalid_coordinates() -> None:
    payload = encode_trip_state(
        TripState(),
        source="test",
        timestamp=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    payload["data"]["current_latitude_deg"] = 91.0

    with pytest.raises(ValueError):
        validate_trip_state(payload)


def test_decoder_accepts_legacy_v1_trip_payload() -> None:
    timestamp = datetime(2026, 9, 10, tzinfo=timezone.utc)
    payload = encode_trip_state(TripState(), source="legacy", timestamp=timestamp)
    payload["version"] = 1
    for field in (
        "boost_time_s",
        "boost_distance_m",
        "boost_fuel_used_m3",
        "peak_boost_pa",
    ):
        payload["data"].pop(field)

    message = decode_trip_state(payload)

    assert message.version == 1
    assert message.data.boost_time_s == pytest.approx(0.0)
    assert message.data.boost_distance_m == pytest.approx(0.0)
    assert message.data.boost_fuel_used_m3 == pytest.approx(0.0)
    assert message.data.peak_boost_pa is None
