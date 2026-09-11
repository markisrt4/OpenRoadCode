# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decode the public automotive trip-state wire contract."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common import decode_timestamp
from .trip_state_message import TripStateData, TripStateMessage
from .trip_state_validator import validate_trip_state


def decode_trip_state(payload: Mapping[str, Any]) -> TripStateMessage:
    """Validate and decode an SI-native trip-state payload."""
    validate_trip_state(payload)
    data = payload["data"]
    return TripStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=TripStateData(
            status=data["status"],
            started_at=None if data["started_at"] is None else decode_timestamp(data["started_at"]),
            ended_at=None if data["ended_at"] is None else decode_timestamp(data["ended_at"]),
            elapsed_s=data["elapsed_s"],
            moving_s=data["moving_s"],
            stopped_s=data["stopped_s"],
            distance_m=data["distance_m"],
            average_speed_m_s=data["average_speed_m_s"],
            maximum_speed_m_s=data["maximum_speed_m_s"],
            fuel_used_m3=data["fuel_used_m3"],
            instantaneous_fuel_consumption_m3_per_m=data["instantaneous_fuel_consumption_m3_per_m"],
            average_fuel_consumption_m3_per_m=data["average_fuel_consumption_m3_per_m"],
            estimated_range_m=data["estimated_range_m"],
            boost_time_s=data.get("boost_time_s", 0.0),
            boost_distance_m=data.get("boost_distance_m", 0.0),
            boost_fuel_used_m3=data.get("boost_fuel_used_m3", 0.0),
            peak_boost_pa=data.get("peak_boost_pa"),
            start_latitude_deg=data["start_latitude_deg"],
            start_longitude_deg=data["start_longitude_deg"],
            current_latitude_deg=data["current_latitude_deg"],
            current_longitude_deg=data["current_longitude_deg"],
            end_latitude_deg=data["end_latitude_deg"],
            end_longitude_deg=data["end_longitude_deg"],
        ),
    )
