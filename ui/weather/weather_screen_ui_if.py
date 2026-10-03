# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent forecast screen lifecycle contracts."""
from abc import abstractmethod
from ui.weather.weather_ui_if import WeatherUiIf
from ui.weather.weather_request_handler_if import WeatherRequestHandlerIf


class WeatherScreenRequestHandlerIf(WeatherRequestHandlerIf):
    """Handle forecast screen visibility and refresh requests."""

    @abstractmethod
    def set_visible(self, visible: bool) -> None:
        """Update screen visibility.

        @param visible Whether the screen is shown.
        """
        ...


class WeatherScreenUiIf(WeatherUiIf):
    """Present forecast state and refresh progress."""

    @abstractmethod
    def set_loading(self, loading: bool) -> None:
        """Present progress.

        @param loading Whether a refresh is pending.
        """
        ...

    @abstractmethod
    def set_weather_status(self, status: str) -> None:
        """Present refresh status.

        @param status Human-readable status or empty string.
        """
        ...
