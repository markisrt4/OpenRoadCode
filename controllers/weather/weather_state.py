# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalized provider-independent weather domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


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
class CurrentWeather:
    temperature_k: float | None = None
    apparent_temperature_k: float | None = None
    relative_humidity: float | None = None
    condition: WeatherCondition = WeatherCondition.UNKNOWN
    precipitation_m: float | None = None
    rain_m: float | None = None
    showers_m: float | None = None
    snowfall_m: float | None = None
    cloud_cover: float | None = None
    pressure_msl_pa: float | None = None
    surface_pressure_pa: float | None = None
    wind_speed_m_s: float | None = None
    wind_direction_deg: float | None = None
    wind_gust_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    timestamp: datetime
    temperature_k: float | None = None
    apparent_temperature_k: float | None = None
    precipitation_probability: float | None = None
    precipitation_m: float | None = None
    condition: WeatherCondition = WeatherCondition.UNKNOWN
    cloud_cover: float | None = None
    wind_speed_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class DailyForecast:
    date: date
    condition: WeatherCondition = WeatherCondition.UNKNOWN
    temperature_high_k: float | None = None
    temperature_low_k: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    precipitation_probability: float | None = None
    wind_speed_max_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherState:
    latitude: float
    longitude: float
    location_name: str
    location_source: str
    source: WeatherSource
    fetched_at: float
    current: CurrentWeather
    hourly: tuple[HourlyForecast, ...] = ()
    daily: tuple[DailyForecast, ...] = ()
