# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode navigation attitude telemetry."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .attitude_state_message import AttitudeStateData, AttitudeStateMessage
from .attitude_state_validator import SCHEMA_VERSION, validate_attitude_state


def encode_attitude_state(
    *,
    timestamp: Mapping[str, int],
    source: str,
    heading_rad: float | None = None,
    pitch_rad: float | None = None,
    roll_rad: float | None = None,
) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {
            "heading_rad": heading_rad,
            "pitch_rad": pitch_rad,
            "roll_rad": roll_rad,
        },
    }
    validate_attitude_state(payload)
    return payload


def decode_attitude_state(payload: Mapping[str, Any]) -> AttitudeStateMessage:
    validate_attitude_state(payload)
    data = payload["data"]
    return AttitudeStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=AttitudeStateData(**{
            name: data[name] for name in AttitudeStateData.__dataclass_fields__
        }),
    )
