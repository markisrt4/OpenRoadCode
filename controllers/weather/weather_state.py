# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalized provider-independent weather domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WeatherCondition(Enum):
    UNKNOWN = "unknown"
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    FREEZING_RAIN = "freezing_rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"


@dataclass(frozen=True, slots=True)
class WeatherLocation:
    latitude: float
    longitude: float
    name: str
    source: str


@dataclass(frozen=True, slots=True)
class WeatherSource:
    provider_id: str
    display_name: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class WeatherState:
    """Normalized weather plus provider payload retained during transition."""

    latitude: float
    longitude: float
    location_name: str
    location_source: str
    source: WeatherSource
    fetched_at: float
    current: dict[str, Any] = field(default_factory=dict)
    hourly: dict[str, Any] = field(default_factory=dict)
    daily: dict[str, Any] = field(default_factory=dict)
