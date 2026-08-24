# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed decoded representation of navigation attitude telemetry."""

from dataclasses import dataclass

from messaging.contracts.common import Timestamp


@dataclass(frozen=True, slots=True)
class AttitudeStateData:
    heading_rad: float | None
    pitch_rad: float | None
    roll_rad: float | None


@dataclass(frozen=True, slots=True)
class AttitudeStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: AttitudeStateData
