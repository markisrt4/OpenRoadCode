# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""State-recording weather UI stub for tests and unavailable frontends."""

from ui.weather.weather_request_handler_if import WeatherRequestHandlerIf
from ui.weather.weather_ui_if import WeatherUiIf, WeatherUiState


class WeatherUiStub(WeatherUiIf):
    def __init__(self) -> None:
        self.state: WeatherUiState | None = None
        self.request_handler: WeatherRequestHandlerIf | None = None

    def set_weather_state(self, state: WeatherUiState | None) -> None:
        self.state = state

    def set_weather_request_handler(
        self,
        handler: WeatherRequestHandlerIf | None,
    ) -> None:
        self.request_handler = handler
