# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode processed barometric telemetry."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .barometric_state_message import BarometricStateData, BarometricStateMessage
from .barometric_state_validator import SCHEMA_VERSION, validate_barometric_state


def encode_barometric_state(*, timestamp: Mapping[str, int], source: str, pressure_pa: float, temperature_c: float | None, altitude_m: float, relative_altitude_m: float, vertical_speed_m_s: float) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {
            "pressure_pa": pressure_pa,
            "temperature_c": temperature_c,
            "altitude_m": altitude_m,
            "relative_altitude_m": relative_altitude_m,
            "vertical_speed_m_s": vertical_speed_m_s,
        },
    }
    validate_barometric_state(payload)
    return payload


def decode_barometric_state(payload: Mapping[str, Any]) -> BarometricStateMessage:
    validate_barometric_state(payload)
    data = payload["data"]
    return BarometricStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=BarometricStateData(**data),
    )
