# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode the public navigation position contract."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.common.timestamp import decode_timestamp, encode_timestamp

from .position_state_message import PositionStateData, PositionStateMessage
from .position_state_validator import SCHEMA_VERSION, validate_position_state


def _degrees_to_radians(value: float | None) -> float | None:
    return None if value is None else math.radians(value)


def encode_position_state(state: PositionState) -> dict[str, Any]:
    """Encode normalized position state into the strict-SI public contract."""
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": encode_timestamp(state.received_at),
        "source": state.source,
        "data": {
            "latitude_rad": _degrees_to_radians(state.latitude_deg),
            "longitude_rad": _degrees_to_radians(state.longitude_deg),
            "altitude_m": state.altitude_m,
            "fix_mode": state.fix_mode,
            "satellites_visible": state.satellites_visible,
            "satellites_used": state.satellites_used,
            "accuracy_m": state.accuracy_m,
            "is_cached": state.is_cached,
        },
    }
    validate_position_state(payload)
    return payload


def decode_position_state(payload: Mapping[str, Any]) -> PositionStateMessage:
    """Validate and decode a public navigation position message."""
    validate_position_state(payload)
    data = payload["data"]
    return PositionStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=PositionStateData(**{name: data[name] for name in PositionStateData.__dataclass_fields__}),
    )
