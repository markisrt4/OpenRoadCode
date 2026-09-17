# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent weather domain and provider contracts."""

from controllers.weather.gpsd_weather_location_provider import GpsdWeatherLocationProvider
from controllers.weather.providers import OpenMeteoWeatherProvider
from controllers.weather.weather_alert import (
    WeatherAlert,
    WeatherAlertCertainty,
    WeatherAlertSeverity,
    WeatherAlertUrgency,
)
from controllers.weather.weather_controller import WeatherController
from controllers.weather.weather_presenter import WeatherPresenter
from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherCondition,
    WeatherLocation,
    WeatherSource,
    WeatherState,
)

__all__ = [
    "CurrentWeather",
    "DailyForecast",
    "GpsdWeatherLocationProvider",
    "HourlyForecast",
    "OpenMeteoWeatherProvider",
    "WeatherAlert",
    "WeatherAlertCertainty",
    "WeatherAlertSeverity",
    "WeatherAlertUrgency",
    "WeatherCondition",
    "WeatherController",
    "WeatherLocation",
    "WeatherPresenter",
    "WeatherProviderIf",
    "WeatherSource",
    "WeatherState",
]
