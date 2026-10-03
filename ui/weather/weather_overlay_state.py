# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable, toolkit-independent weather map presentation in SI units."""

from dataclasses import dataclass
from datetime import datetime

from ui.navigation.map_ui_if import GeoPoint


@dataclass(frozen=True, slots=True)
class WeatherColorStop:
    """One palette stop in Kelvin for temperature or m/s for wind."""

    value_si: float
    rgb: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class WeatherRaster:
    tile_url: str
    frame_time: int
    opacity: float = 0.45
    max_zoom: int = 9


@dataclass(frozen=True, slots=True)
class ModelWeatherOverlayState:
    kind: str = "off"
    status: str = "Select a weather overlay"
    raster: WeatherRaster | None = None
    legend: tuple[WeatherColorStop, ...] = ()
    valid_at: datetime | None = None
    loading: bool = False


@dataclass(frozen=True, slots=True)
class CityWeatherPoint:
    """One named point; value_si is Kelvin, m/s or precipitation metres."""

    name: str
    position: GeoPoint
    value_si: float | None
    city_id: str = ""


@dataclass(frozen=True, slots=True)
class CityWeatherHour:
    """One hourly model estimate or forecast, normalized to SI."""

    valid_at: datetime
    temperature_k: float | None
    wind_speed_m_s: float | None
    precipitation_m: float | None


@dataclass(frozen=True, slots=True)
class CityWeatherDetails:
    """Selected city's cached detail rows and window summary in SI."""

    city_id: str
    name: str
    selected_at: datetime
    temperature_k: float | None
    wind_speed_m_s: float | None
    precipitation_m: float | None
    hours: tuple[CityWeatherHour, ...] = ()
    fetched_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CityWeatherOverlayState:
    """Hourly selection and complete city values; anchor is an aware UTC time."""

    enabled: bool = False
    visible: bool = False
    kind: str = "temperature"
    period: str = "past"
    hours: int = 1
    playing: bool = False
    status: str = "Enable city weather, then pan or zoom to an area"
    anchor: datetime | None = None
    points: tuple[CityWeatherPoint, ...] = ()
    can_refresh: bool = False
    can_play: bool = False
    details: CityWeatherDetails | None = None


@dataclass(frozen=True, slots=True)
class RouteWeatherPoint:
    """An arrival forecast; rain_probability is a fraction between zero and one."""

    position: GeoPoint
    arrival: datetime
    temperature_k: float | None
    rain_probability: float | None
    wind_speed_m_s: float | None
    condition: str


@dataclass(frozen=True, slots=True)
class RouteWeatherOverlayState:
    enabled: bool = False
    layers: frozenset[str] = frozenset({"temperature", "rain", "wind"})
    status: str = "Start a route to see weather along the way"
    points: tuple[RouteWeatherPoint, ...] = ()
