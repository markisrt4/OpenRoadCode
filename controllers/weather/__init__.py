# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent weather retrieval and snapshot caching."""

from pathlib import Path

from controllers.weather.open_meteo_weather_controller import (
    OpenMeteoWeatherController,
)
from controllers.weather.gpsd_weather_location_provider import (
    GpsdWeatherLocationProvider,
)
from controllers.weather.weather_snapshot import WeatherLocation, WeatherSnapshot
from controllers.weather.weather_snapshot_cache import WeatherSnapshotCache

DEFAULT_WEATHER_CACHE_DIRECTORY = (
    Path.home() / ".cache" / "openroadcode" / "weather"
)

__all__ = [
    "OpenMeteoWeatherController",
    "DEFAULT_WEATHER_CACHE_DIRECTORY",
    "GpsdWeatherLocationProvider",
    "WeatherLocation",
    "WeatherSnapshot",
    "WeatherSnapshotCache",
]
