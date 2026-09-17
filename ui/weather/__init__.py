# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent weather presentation contracts."""

from ui.weather.weather_alert_ui_if import WeatherAlertUiEvent, WeatherAlertUiIf
from ui.weather.weather_request_handler_if import WeatherRequestHandlerIf
from ui.weather.weather_ui_if import (
    WeatherCurrentUiState,
    WeatherDailyUiState,
    WeatherHourlyUiState,
    WeatherUiIf,
    WeatherUiState,
)

__all__ = [
    "WeatherAlertUiEvent",
    "WeatherAlertUiIf",
    "WeatherCurrentUiState",
    "WeatherDailyUiState",
    "WeatherHourlyUiState",
    "WeatherRequestHandlerIf",
    "WeatherUiIf",
    "WeatherUiState",
]
