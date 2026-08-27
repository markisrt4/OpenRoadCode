# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for derived navigation motion messages."""

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1
DATA_FIELDS = {
    "heading_rad",
    "ground_speed_m_s",
    "course_rad",
    "vertical_speed_m_s",
    "turn_rate_rad_s",
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


def validate_motion_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("motion message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError("unsupported motion schema version")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    data = payload["data"]
    if not isinstance(data, Mapping) or set(data) != DATA_FIELDS:
        raise ValueError("motion data has missing or unknown fields")
    heading = _optional_finite(data, "heading_rad")
    speed = _optional_finite(data, "ground_speed_m_s")
    course = _optional_finite(data, "course_rad")
    _optional_finite(data, "vertical_speed_m_s")
    _optional_finite(data, "turn_rate_rad_s")
    if heading is not None and not 0 <= heading < 2 * math.pi:
        raise ValueError("heading_rad must be in range 0..2*pi")
    if course is not None and not 0 <= course < 2 * math.pi:
        raise ValueError("course_rad must be in range 0..2*pi")
    if speed is not None and speed < 0:
        raise ValueError("ground_speed_m_s cannot be negative")
    if not isinstance(data["is_cached"], bool):
        raise ValueError("is_cached must be a boolean")
