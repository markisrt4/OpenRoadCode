# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public ambient-light state contract."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import validate_timestamp

SCHEMA_VERSION = 1
DATA_FIELDS = {"illuminance_lux"}


def validate_ambient_light_state(payload: Mapping[str, Any]) -> None:
    if set(payload) != {"version", "timestamp", "source", "data"}:
        raise ValueError("ambient-light message envelope has missing or unknown fields")
    if payload["version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported ambient-light schema version: {payload['version']!r}")
    if not isinstance(payload["timestamp"], Mapping):
        raise ValueError("timestamp must be an object")
    validate_timestamp(payload["timestamp"])
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")
    if not isinstance(payload["data"], Mapping):
        raise ValueError("data must be an object")
    data = payload["data"]
    if set(data) != DATA_FIELDS:
        raise ValueError("ambient-light data has missing or unknown fields")
    illuminance = data["illuminance_lux"]
    if isinstance(illuminance, bool) or not isinstance(illuminance, (int, float)):
        raise ValueError("illuminance_lux must be a finite number")
    illuminance = float(illuminance)
    if not math.isfinite(illuminance):
        raise ValueError("illuminance_lux must be finite")
    if illuminance < 0.0:
        raise ValueError("illuminance_lux must be non-negative")
