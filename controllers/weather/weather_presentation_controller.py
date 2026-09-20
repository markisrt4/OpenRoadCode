# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bridge WeatherController refresh requests to the weather presenter."""

from controllers.weather.weather_controller import WeatherController
from controllers.weather.weather_presenter import WeatherPresenter
from ui.weather import WeatherRequestHandlerIf


class WeatherPresentationController(WeatherRequestHandlerIf):
    def __init__(self, controller: WeatherController, presenter: WeatherPresenter) -> None:
        self._controller = controller
        self._presenter = presenter

    def request_refresh(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._presenter.present(self._controller.refresh())
