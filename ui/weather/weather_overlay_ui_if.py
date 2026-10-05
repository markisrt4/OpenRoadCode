# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation boundary shared by weather controls and map frontends."""

from abc import ABC, abstractmethod

from ui.weather.weather_overlay_state import CityWeatherOverlayState, ModelWeatherOverlayState, RouteWeatherOverlayState


class WeatherOverlayUiIf(ABC):
    """Receive immutable SI weather state without providers or rendering commands."""

    @abstractmethod
    def set_city_weather_state(self, state: CityWeatherOverlayState) -> None:
        """Present selected hourly city values.

        @param state Complete city overlay snapshot, with Kelvin, m/s or metres.
        """
        ...

    @abstractmethod
    def set_model_weather_state(self, state: ModelWeatherOverlayState) -> None:
        """Present a full-area forecast raster and SI legend.

        @param state Complete model heatmap snapshot.
        """
        ...

    @abstractmethod
    def set_route_weather_state(self, state: RouteWeatherOverlayState) -> None:
        """Present weather at estimated route arrival times.

        @param state Complete route checkpoint snapshot in SI units.
        """
        ...
