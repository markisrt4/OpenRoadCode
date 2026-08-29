# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode ambient-light telemetry."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .ambient_light_state_message import AmbientLightStateData, AmbientLightStateMessage
from .ambient_light_state_validator import SCHEMA_VERSION, validate_ambient_light_state


def encode_ambient_light_state(
    *,
    timestamp: Mapping[str, int],
    source: str,
    illuminance_lux: float,
) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {"illuminance_lux": illuminance_lux},
    }
    validate_ambient_light_state(payload)
    return payload


def decode_ambient_light_state(payload: Mapping[str, Any]) -> AmbientLightStateMessage:
    validate_ambient_light_state(payload)
    data = payload["data"]
    return AmbientLightStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=AmbientLightStateData(**data),
    )
