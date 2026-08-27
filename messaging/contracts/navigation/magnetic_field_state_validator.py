# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for magnetic-field navigation telemetry."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1


def validate_magnetic_field_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("magnetic field message has unexpected fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError("unsupported magnetic field schema version")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    data = payload["data"]
    if not isinstance(data, Mapping) or set(data) != {"magnetic_field_ut"}:
        raise ValueError("data must contain exactly magnetic_field_ut")
    vector = data["magnetic_field_ut"]
    if not isinstance(vector, Mapping) or set(vector) != {"x", "y", "z"}:
        raise ValueError("magnetic_field_ut must contain exactly x, y, z")
    for axis in ("x", "y", "z"):
        value = vector[axis]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"magnetic_field_ut.{axis} must be numeric")
