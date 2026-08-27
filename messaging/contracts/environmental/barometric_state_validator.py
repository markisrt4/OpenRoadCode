# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public barometric state contract."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1
DATA_FIELDS = {"pressure_pa", "temperature_c", "altitude_m", "relative_altitude_m", "vertical_speed_m_s"}


def _finite(data: Mapping[str, Any], name: str, *, optional: bool = False) -> float | None:
    value = data[name]
    if optional and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number" + (" or null" if optional else ""))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def validate_barometric_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("barometric message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported barometric schema version: {payload['version']!r}")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    if not isinstance(payload["data"], Mapping):
        raise ValueError("data must be an object")
    data = payload["data"]
    if set(data) != DATA_FIELDS:
        raise ValueError("barometric data has missing or unknown fields")
    pressure = _finite(data, "pressure_pa")
    if pressure is not None and pressure <= 0.0:
        raise ValueError("pressure_pa must be greater than zero")
    _finite(data, "temperature_c", optional=True)
    _finite(data, "altitude_m")
    _finite(data, "relative_altitude_m")
    _finite(data, "vertical_speed_m_s")
