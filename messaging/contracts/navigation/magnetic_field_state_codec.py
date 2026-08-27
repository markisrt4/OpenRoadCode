# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode magnetic-field navigation telemetry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .magnetic_field_state_message import MagneticFieldStateMessage, MagneticFieldVector
from .magnetic_field_state_validator import SCHEMA_VERSION, validate_magnetic_field_state


def encode_magnetic_field_state(*, timestamp: Mapping[str, int], source: str,
                                magnetic_field_ut: Mapping[str, float]) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {"magnetic_field_ut": {axis: magnetic_field_ut[axis] for axis in ("x", "y", "z")}},
    }
    validate_magnetic_field_state(payload)
    return payload


def decode_magnetic_field_state(payload: Mapping[str, Any]) -> MagneticFieldStateMessage:
    validate_magnetic_field_state(payload)
    vector = payload["data"]["magnetic_field_ut"]
    return MagneticFieldStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        magnetic_field_ut=MagneticFieldVector(**vector),
    )
