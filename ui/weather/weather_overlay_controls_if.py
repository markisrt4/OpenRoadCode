# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactive weather overlays add a semantic request binding to presentation."""

from abc import abstractmethod

from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf


class WeatherOverlayControlsIf(WeatherOverlayUiIf):
    """Present state and bind actions while remaining independent of controller classes."""

    @abstractmethod
    def set_weather_overlay_request_handler(self, handler: WeatherOverlayRequestHandlerIf | None) -> None:
        """Connect or disconnect weather actions.

        @param handler Semantic request consumer, or None to disable actions.
        """
        ...
