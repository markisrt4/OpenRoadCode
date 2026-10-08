# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""State-recording weather overlay sink for headless views and tests."""

from ui.weather.weather_overlay_state import CityWeatherOverlayState, ModelWeatherOverlayState, RouteWeatherOverlayState
from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf


class WeatherOverlayUiStub(WeatherOverlayUiIf):
    def __init__(self):
        self.city_state = CityWeatherOverlayState()
        self.model_state = ModelWeatherOverlayState()
        self.route_state = RouteWeatherOverlayState()

    def set_city_weather_state(self, state):
        self.city_state = state

    def set_model_weather_state(self, state):
        self.model_state = state

    def set_route_weather_state(self, state):
        self.route_state = state
