# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode the derived navigation motion contract."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .motion_state_message import MotionStateData, MotionStateMessage
from .motion_state_validator import SCHEMA_VERSION, validate_motion_state


def encode_motion_state(
    *,
    timestamp: Mapping[str, int],
    source: str,
    heading_rad=None,
    ground_speed_m_s=None,
    course_rad=None,
    vertical_speed_m_s=None,
    turn_rate_rad_s=None,
    is_cached=False,
) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {
            "heading_rad": heading_rad,
            "ground_speed_m_s": ground_speed_m_s,
            "course_rad": course_rad,
            "vertical_speed_m_s": vertical_speed_m_s,
            "turn_rate_rad_s": turn_rate_rad_s,
            "is_cached": is_cached,
        },
    }
    validate_motion_state(payload)
    return payload


def decode_motion_state(payload: Mapping[str, Any]) -> MotionStateMessage:
    validate_motion_state(payload)
    data = payload["data"]
    return MotionStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=MotionStateData(
            **{name: data[name] for name in MotionStateData.__dataclass_fields__}
        ),
    )
