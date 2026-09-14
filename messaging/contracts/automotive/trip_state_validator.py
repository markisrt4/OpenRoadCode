# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public automotive trip-state wire contract."""

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common import validate_timestamp
from .trip_state_codec import SCHEMA_VERSION

TOP_LEVEL_FIELDS = {"version", "timestamp", "source", "data"}
V1_DATA_FIELDS = {
    "status", "started_at", "ended_at", "elapsed_s", "moving_s", "stopped_s",
    "distance_m", "average_speed_m_s", "maximum_speed_m_s", "fuel_used_m3",
    "instantaneous_fuel_consumption_m3_per_m", "average_fuel_consumption_m3_per_m",
    "estimated_range_m", "start_latitude_deg", "start_longitude_deg",
    "current_latitude_deg", "current_longitude_deg", "end_latitude_deg",
    "end_longitude_deg",
}
DATA_FIELDS = V1_DATA_FIELDS | {
    "boost_time_s", "boost_distance_m", "boost_fuel_used_m3", "peak_boost_pa",
}
OPTIONAL_NUMERIC_FIELDS = DATA_FIELDS - {
    "status", "started_at", "ended_at", "elapsed_s", "moving_s", "stopped_s", "distance_m"
}
VALID_STATUSES = {"idle", "active", "paused", "complete"}


def _number(name: str, value: Any, *, optional: bool = True) -> None:
    if value is None and optional:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number" + (" or null" if optional else ""))


def validate_trip_state(payload: Mapping[str, Any]) -> None:
    """Raise ValueError unless payload exactly satisfies trip contract version 1."""
    if not isinstance(payload, Mapping) or set(payload) != TOP_LEVEL_FIELDS:
        raise ValueError("trip state envelope contains missing or unknown fields")
    version = payload["version"]
    if isinstance(version, bool) or version not in {1, SCHEMA_VERSION}:
        raise ValueError(f"unsupported trip state version: {version}")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("trip state timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"].strip():
        raise ValueError("trip state source must be a non-empty string")

    data = payload["data"]
    expected_fields = V1_DATA_FIELDS if version == 1 else DATA_FIELDS
    if not isinstance(data, Mapping) or set(data) != expected_fields:
        raise ValueError("trip state data contains missing or unknown fields")
    if data["status"] not in VALID_STATUSES:
        raise ValueError("trip state status is invalid")
    for name in ("started_at", "ended_at"):
        value = data[name]
        if value is not None:
            if not isinstance(value, Mapping):
                raise ValueError(f"{name} must be a timestamp or null")
            validate_timestamp(value)
    for name in ("elapsed_s", "moving_s", "stopped_s", "distance_m"):
        _number(name, data[name], optional=False)
        if data[name] < 0.0:
            raise ValueError(f"{name} cannot be negative")
    for name in OPTIONAL_NUMERIC_FIELDS & expected_fields:
        _number(name, data[name])
    for name in (
        {
            "average_speed_m_s", "maximum_speed_m_s", "fuel_used_m3",
            "instantaneous_fuel_consumption_m3_per_m",
            "average_fuel_consumption_m3_per_m", "estimated_range_m",
            "boost_time_s", "boost_distance_m", "boost_fuel_used_m3",
            "peak_boost_pa",
        }
        & expected_fields
    ):
        if data[name] is not None and data[name] < 0.0:
            raise ValueError(f"{name} cannot be negative")
    for name in ("start_latitude_deg", "current_latitude_deg", "end_latitude_deg"):
        if data[name] is not None and not -90.0 <= data[name] <= 90.0:
            raise ValueError(f"{name} must be in range -90..90")
    for name in ("start_longitude_deg", "current_longitude_deg", "end_longitude_deg"):
        if data[name] is not None and not -180.0 <= data[name] <= 180.0:
            raise ValueError(f"{name} must be in range -180..180")
