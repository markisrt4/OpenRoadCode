# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for framed IMU telemetry."""

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

from .frames import validate_frame_id

SCHEMA_VERSION = 1
DATA_FIELDS = {
    "acceleration_m_s2",
    "linear_acceleration_m_s2",
    "angular_velocity_rad_s",
}
VECTOR_FIELDS = {"x", "y", "z"}


def _validate_vector(data: Mapping[str, Any], name: str) -> None:
    vector = data[name]
    if not isinstance(vector, Mapping) or set(vector) != VECTOR_FIELDS:
        raise ValueError(f"{name} must contain exactly x, y, and z")
    for axis in VECTOR_FIELDS:
        value = vector[axis]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}.{axis} must be a finite number")
        if not math.isfinite(float(value)):
            raise ValueError(f"{name}.{axis} must be finite")


def validate_imu_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "frame_id", "data"}:
        raise ValueError("IMU message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError("unsupported IMU schema version")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    validate_frame_id(payload["frame_id"])
    data = payload["data"]
    if not isinstance(data, Mapping) or set(data) != DATA_FIELDS:
        raise ValueError("IMU data has missing or unknown fields")
    for name in DATA_FIELDS:
        _validate_vector(data, name)
