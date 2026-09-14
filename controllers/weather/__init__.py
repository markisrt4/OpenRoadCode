# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent weather retrieval and snapshot caching."""

from importlib import import_module
from typing import Any

from common.xdg_paths import openroadcode_cache_dir
from controllers.weather.weather_snapshot import WeatherLocation, WeatherSnapshot
from controllers.weather.weather_snapshot_cache import WeatherSnapshotCache

DEFAULT_WEATHER_CACHE_DIRECTORY = openroadcode_cache_dir("weather")

__all__ = [
    "OpenMeteoWeatherController",
    "DEFAULT_WEATHER_CACHE_DIRECTORY",
    "GpsdWeatherLocationProvider",
    "WeatherLocation",
    "WeatherSnapshot",
    "WeatherSnapshotCache",
]

_LAZY_EXPORTS = {
    "OpenMeteoWeatherController": (
        "controllers.weather.open_meteo_weather_controller",
        "OpenMeteoWeatherController",
    ),
    "GpsdWeatherLocationProvider": (
        "controllers.weather.gpsd_weather_location_provider",
        "GpsdWeatherLocationProvider",
    ),
}


def __getattr__(name: str) -> Any:
    """Load optional weather providers only when explicitly requested."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
