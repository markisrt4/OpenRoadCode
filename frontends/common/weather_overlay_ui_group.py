# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fan immutable weather state out to controls and a map adapter."""

from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf


class WeatherOverlayUiGroup(WeatherOverlayUiIf):
    """Send the same contract snapshot to each registered frontend."""

    def __init__(self, *views: WeatherOverlayUiIf):
        if any(not isinstance(view, WeatherOverlayUiIf) for view in views):
            raise TypeError("Weather overlay views must implement WeatherOverlayUiIf")
        self._views = views

    def set_city_weather_state(self, state):
        for view in self._views:
            view.set_city_weather_state(state)

    def set_model_weather_state(self, state):
        for view in self._views:
            view.set_model_weather_state(state)

    def set_route_weather_state(self, state):
        for view in self._views:
            view.set_route_weather_state(state)
