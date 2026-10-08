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
    "WeatherOverlayControlsIf", "WeatherOverlayRequestHandlerIf", "WeatherOverlayUiIf",
    "RadarControlsIf", "RadarRequestHandlerIf", "RadarUiIf", "RadarUiState", "RadarPalette",
    "WeatherAlertUiEvent",
    "WeatherAlertUiIf",
    "WeatherCurrentUiState",
    "WeatherDailyUiState",
    "WeatherHourlyUiState",
    "WeatherRequestHandlerIf",
    "WeatherUiIf",
    "WeatherUiState",
]

from ui.weather.weather_overlay_controls_if import WeatherOverlayControlsIf
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from ui.weather.radar_controls_if import RadarControlsIf
from ui.weather.radar_request_handler_if import RadarRequestHandlerIf
from ui.weather.radar_ui_if import RadarUiIf, RadarUiState, RadarPalette
