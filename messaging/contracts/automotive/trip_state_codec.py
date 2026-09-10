# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode the public automotive trip-state wire contract."""

from datetime import datetime, timezone
from typing import Any

from controllers.automotive.trip_state import TripState
from messaging.contracts.common import encode_timestamp

SCHEMA_VERSION = 1


def encode_trip_state(
    state: TripState,
    *,
    source: str = "trip-service",
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Encode an SI-normalized trip snapshot."""
    observed_at = timestamp or state.ended_at or datetime.now(timezone.utc)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": encode_timestamp(observed_at),
        "source": source,
        "data": {
            "status": state.status.value,
            "started_at": None if state.started_at is None else encode_timestamp(state.started_at),
            "ended_at": None if state.ended_at is None else encode_timestamp(state.ended_at),
            "elapsed_s": state.elapsed_s,
            "moving_s": state.moving_s,
            "stopped_s": state.stopped_s,
            "distance_m": state.distance_m,
            "average_speed_m_s": state.average_speed_m_s,
            "maximum_speed_m_s": state.maximum_speed_m_s,
            "fuel_used_m3": state.fuel_used_m3,
            "instantaneous_fuel_consumption_m3_per_m": state.instantaneous_fuel_consumption_m3_per_m,
            "average_fuel_consumption_m3_per_m": state.average_fuel_consumption_m3_per_m,
            "estimated_range_m": state.estimated_range_m,
            "start_latitude_deg": state.start_latitude_deg,
            "start_longitude_deg": state.start_longitude_deg,
            "current_latitude_deg": state.current_latitude_deg,
            "current_longitude_deg": state.current_longitude_deg,
            "end_latitude_deg": state.end_latitude_deg,
            "end_longitude_deg": state.end_longitude_deg,
        },
    }
    from .trip_state_validator import validate_trip_state
    validate_trip_state(payload)
    return payload
