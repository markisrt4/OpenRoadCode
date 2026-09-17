# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode the public weather alert contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from controllers.weather import WeatherAlert

from .weather_alert_message import WeatherAlertData, WeatherAlertMessage
from .weather_alert_validator import SCHEMA_VERSION, validate_weather_alert


def encode_weather_alert(alert: WeatherAlert) -> dict[str, Any]:
    payload = {
        "version": SCHEMA_VERSION,
        "source": alert.source,
        "data": {
            "alert_id": alert.alert_id,
            "event": alert.event,
            "headline": alert.headline,
            "description": alert.description,
            "instruction": alert.instruction,
            "severity": alert.severity.value,
            "urgency": alert.urgency.value,
            "certainty": alert.certainty.value,
            "effective_at": alert.effective_at.isoformat(),
            "onset_at": None if alert.onset_at is None else alert.onset_at.isoformat(),
            "expires_at": None if alert.expires_at is None else alert.expires_at.isoformat(),
            "sender": alert.sender,
        },
    }
    validate_weather_alert(payload)
    return payload


def decode_weather_alert(payload: Mapping[str, Any]) -> WeatherAlertMessage:
    validate_weather_alert(payload)
    data = payload["data"]
    return WeatherAlertMessage(
        version=payload["version"],
        source=payload["source"],
        data=WeatherAlertData(
            **{name: data[name] for name in WeatherAlertData.__dataclass_fields__}
        ),
    )
