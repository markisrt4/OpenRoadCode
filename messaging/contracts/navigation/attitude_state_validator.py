# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for navigation attitude telemetry."""

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1
DATA_FIELDS = {"heading_rad", "pitch_rad", "roll_rad"}


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


def validate_attitude_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("attitude message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError("unsupported attitude schema version")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    data = payload["data"]
    if not isinstance(data, Mapping) or set(data) != DATA_FIELDS:
        raise ValueError("attitude data has missing or unknown fields")
    heading = _optional_finite(data, "heading_rad")
    pitch = _optional_finite(data, "pitch_rad")
    roll = _optional_finite(data, "roll_rad")
    if heading is not None and not 0.0 <= heading < 2.0 * math.pi:
        raise ValueError("heading_rad must be in range 0..2*pi")
    if pitch is not None and not -math.pi / 2.0 <= pitch <= math.pi / 2.0:
        raise ValueError("pitch_rad must be in range -pi/2..pi/2")
    if roll is not None and not -math.pi <= roll <= math.pi:
        raise ValueError("roll_rad must be in range -pi..pi")
