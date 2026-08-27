# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed public navigation position message."""

from dataclasses import dataclass

from messaging.contracts.common.timestamp import Timestamp


@dataclass(frozen=True, slots=True)
class PositionStateData:
    latitude_rad: float | None
    longitude_rad: float | None
    altitude_m: float | None
    fix_mode: int | None
    satellites_visible: int | None
    satellites_used: int | None
    accuracy_m: float | None
    is_cached: bool


@dataclass(frozen=True, slots=True)
class PositionStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: PositionStateData
