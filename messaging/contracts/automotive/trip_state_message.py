# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed decoded representation of the public trip-state contract."""

from dataclasses import dataclass

from messaging.contracts.common import Timestamp


@dataclass(frozen=True, slots=True)
class TripStateData:
    status: str
    started_at: Timestamp | None
    ended_at: Timestamp | None
    elapsed_s: float
    moving_s: float
    stopped_s: float
    distance_m: float
    average_speed_m_s: float | None
    maximum_speed_m_s: float | None
    fuel_used_m3: float | None
    instantaneous_fuel_consumption_m3_per_m: float | None
    average_fuel_consumption_m3_per_m: float | None
    estimated_range_m: float | None
    boost_time_s: float
    boost_distance_m: float
    boost_fuel_used_m3: float
    peak_boost_pa: float | None
    start_latitude_deg: float | None
    start_longitude_deg: float | None
    current_latitude_deg: float | None
    current_longitude_deg: float | None
    end_latitude_deg: float | None
    end_longitude_deg: float | None


@dataclass(frozen=True, slots=True)
class TripStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: TripStateData
