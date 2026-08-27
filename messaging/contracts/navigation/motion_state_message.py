# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed public derived navigation motion message."""

from dataclasses import dataclass

from messaging.contracts.common.timestamp import Timestamp


@dataclass(frozen=True, slots=True)
class MotionStateData:
    heading_rad: float | None
    ground_speed_m_s: float | None
    course_rad: float | None
    vertical_speed_m_s: float | None
    turn_rate_rad_s: float | None
    is_cached: bool


@dataclass(frozen=True, slots=True)
class MotionStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: MotionStateData
