# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic request handler and lifecycle for the three map-weather features."""

from ui.ui_dispatcher_if import UiDispatcherIf
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf


class WeatherOverlayController(WeatherOverlayRequestHandlerIf):
    """Translate UI intent to domain controllers without coupling them to Tk widgets."""

    def __init__(self, dispatcher: UiDispatcherIf, city, model, route):
        self._dispatcher = dispatcher
        self._city, self._model, self._route = city, model, route
        self._visible = self._closed = False
        self._generation = 0

    def request_city_enabled(self, enabled: bool) -> None:
        self._city.set_enabled(enabled)

    def request_city_selection(self, kind: str, period: str, hours: int) -> None:
        self._city.set_playing(False)
        self._city.select(kind=kind, period=period, hours=hours)

    def request_city_playback(self, playing: bool) -> None:
        self._city.set_playing(playing)

    def request_city_refresh(self) -> None:
        self._city.refresh()

    def request_city_details(self, city_id: str | None) -> None:
        self._city.select_details(city_id)

    def request_model_selection(self, kind: str) -> None:
        self._model.select(kind)

    def request_model_refresh(self) -> None:
        self._model.refresh()

    def request_route_enabled(self, enabled: bool) -> None:
        self._route.set_enabled(enabled)

    def request_route_layers(self, layers: frozenset[str]) -> None:
        self._route.set_layers(layers)

    def request_route_refresh(self) -> None:
        self._route.refresh()

    def request_navigation_visible(self, visible: bool) -> None:
        if self._closed:
            return
        self._visible = visible
        self._generation += 1
        if visible:
            self._city.show()
            self._poll(self._generation)
        else:
            self._city.hide()

    def request_replay(self) -> None:
        if not self._closed and self._visible:
            self._city.publish()
            self._model.publish()
            self._route.publish()

    def _poll(self, generation):
        if self._closed or not self._visible or generation != self._generation:
            return
        self._route.refresh()
        self._model.refresh()
        self._dispatcher.schedule_ui_callback(900000, lambda: self._poll(generation))

    def close(self):
        """Release all overlay controllers when the composition shuts down."""
        if self._closed:
            return
        self.request_navigation_visible(False)
        self._closed = True
        self._generation += 1
        try:
            self._city.close()
        finally:
            try:
                self._model.close()
            finally:
                self._route.close()
