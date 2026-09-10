# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable SI-normalized automotive trip state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TripStatus(Enum):
    """Lifecycle state for the currently tracked trip."""

    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class TripState:
    """Snapshot of derived automotive trip measurements.

    Durations are seconds, distances are metres, speeds are metres per second,
    and fuel volume is cubic metres. Fuel-consumption values use cubic metres
    per metre so the public domain remains SI-normalized.
    """

    status: TripStatus = TripStatus.IDLE

    started_at: datetime | None = None
    ended_at: datetime | None = None

    elapsed_s: float = 0.0
    moving_s: float = 0.0
    stopped_s: float = 0.0

    distance_m: float = 0.0
    average_speed_m_s: float | None = None
    maximum_speed_m_s: float | None = None

    fuel_used_m3: float | None = None
    instantaneous_fuel_consumption_m3_per_m: float | None = None
    average_fuel_consumption_m3_per_m: float | None = None
    estimated_range_m: float | None = None

    start_latitude_deg: float | None = None
    start_longitude_deg: float | None = None
    current_latitude_deg: float | None = None
    current_longitude_deg: float | None = None
    end_latitude_deg: float | None = None
    end_longitude_deg: float | None = None
