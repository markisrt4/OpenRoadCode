# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed weather snapshot shared by applications and frontends."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WeatherLocation:
    """Describe coordinates selected for a weather request."""

    latitude: float
    longitude: float
    name: str
    source: str


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    """Represent one fetched forecast and its location metadata."""

    latitude: float
    longitude: float
    location_name: str
    source: str
    fetched_at: float
    forecast: dict[str, Any]
