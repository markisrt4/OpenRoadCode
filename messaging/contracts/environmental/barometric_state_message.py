# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decoded barometric state bus message types."""

from __future__ import annotations

from dataclasses import dataclass

from messaging.contracts.common.timestamp import Timestamp


@dataclass(frozen=True, slots=True)
class BarometricStateData:
    pressure_pa: float
    temperature_c: float | None
    altitude_m: float
    relative_altitude_m: float
    vertical_speed_m_s: float


@dataclass(frozen=True, slots=True)
class BarometricStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: BarometricStateData
