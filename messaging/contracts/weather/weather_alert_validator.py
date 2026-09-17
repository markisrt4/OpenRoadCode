# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public weather alert contract."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from controllers.weather import (
    WeatherAlertCertainty,
    WeatherAlertSeverity,
    WeatherAlertUrgency,
)

SCHEMA_VERSION = 1


def validate_weather_alert(payload: Mapping[str, Any]) -> None:
    if payload.get("version") != SCHEMA_VERSION:
        raise ValueError("unsupported weather alert schema version")
    if not isinstance(payload.get("source"), str) or not payload["source"]:
        raise ValueError("source must be a non-empty string")

    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError("data must be an object")

    required = {
        "alert_id",
        "event",
        "headline",
        "description",
        "instruction",
        "severity",
        "urgency",
        "certainty",
        "effective_at",
        "onset_at",
        "expires_at",
        "sender",
    }
    if set(data) != required:
        raise ValueError("weather alert data fields do not match schema")

    for name in ("alert_id", "event", "headline", "description", "sender"):
        if not isinstance(data[name], str) or not data[name]:
            raise ValueError(f"{name} must be a non-empty string")

    instruction = data["instruction"]
    if instruction is not None and not isinstance(instruction, str):
        raise ValueError("instruction must be null or a string")

    _validate_enum(data["severity"], WeatherAlertSeverity, "severity")
    _validate_enum(data["urgency"], WeatherAlertUrgency, "urgency")
    _validate_enum(data["certainty"], WeatherAlertCertainty, "certainty")

    _validate_timestamp(data["effective_at"], "effective_at", nullable=False)
    _validate_timestamp(data["onset_at"], "onset_at", nullable=True)
    _validate_timestamp(data["expires_at"], "expires_at", nullable=True)


def _validate_enum(value: Any, enum_type: type, name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    try:
        enum_type(value)
    except ValueError as error:
        raise ValueError(f"unsupported weather alert {name}: {value}") from error


def _validate_timestamp(value: Any, name: str, *, nullable: bool) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone offset")
