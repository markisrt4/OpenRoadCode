# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public navigation position contract."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1
DATA_FIELDS = {
    "latitude_rad",
    "longitude_rad",
    "altitude_m",
    "speed_m_s",
    "course_rad",
    "fix_mode",
    "satellites_visible",
    "satellites_used",
    "accuracy_m",
    "is_cached",
}


def _optional_finite(data: Mapping[str, Any], name: str) -> float | None:
    value = data[name]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number or null")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _optional_nonnegative_int(data: Mapping[str, Any], name: str) -> int | None:
    value = data[name]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer or null")
    return value


def validate_position_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("position message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported position schema version: {payload['version']!r}")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    if not isinstance(payload["data"], Mapping):
        raise ValueError("data must be an object")

    data = payload["data"]
    if set(data) != DATA_FIELDS:
        raise ValueError("position data has missing or unknown fields")

    latitude = _optional_finite(data, "latitude_rad")
    longitude = _optional_finite(data, "longitude_rad")
    altitude = _optional_finite(data, "altitude_m")
    speed = _optional_finite(data, "speed_m_s")
    course = _optional_finite(data, "course_rad")
    accuracy = _optional_finite(data, "accuracy_m")

    if latitude is not None and not -math.pi / 2 <= latitude <= math.pi / 2:
        raise ValueError("latitude_rad must be in range -pi/2..pi/2")
    if longitude is not None and not -math.pi <= longitude <= math.pi:
        raise ValueError("longitude_rad must be in range -pi..pi")
    if speed is not None and speed < 0:
        raise ValueError("speed_m_s cannot be negative")
    if course is not None and not 0 <= course < 2 * math.pi:
        raise ValueError("course_rad must be in range 0..2*pi")
    if accuracy is not None and accuracy < 0:
        raise ValueError("accuracy_m cannot be negative")
    # Altitude is intentionally signed: positions below the reference datum exist.
    _ = altitude

    fix_mode = _optional_nonnegative_int(data, "fix_mode")
    visible = _optional_nonnegative_int(data, "satellites_visible")
    used = _optional_nonnegative_int(data, "satellites_used")
    if fix_mode is not None and fix_mode not in (1, 2, 3):
        raise ValueError("fix_mode must be 1, 2, 3, or null")
    if visible is not None and used is not None and used > visible:
        raise ValueError("satellites_used cannot exceed satellites_visible")
    if not isinstance(data["is_cached"], bool):
        raise ValueError("is_cached must be a boolean")
