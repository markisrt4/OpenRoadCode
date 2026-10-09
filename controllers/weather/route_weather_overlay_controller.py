# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Asynchronous route forecasts presented through immutable UI state."""

import logging

from datetime import datetime, timezone
import math
import threading
from common.logging.structured import operation
from controllers.weather.weather_logging import WeatherLog

from controllers.weather.route_weather import sample_route
from ui.navigation import GeoPoint
from ui.ui_dispatcher_if import UiDispatcherIf
from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from ui.weather.weather_overlay_state import RouteWeatherOverlayState, RouteWeatherPoint


class RouteWeatherOverlayController:
    """Own route sampling, request invalidation and provider work outside all frontends."""

    def __init__(self, dispatcher: UiDispatcherIf, route_handler, presentation, provider, ui: WeatherOverlayUiIf):
        self._host, self._provider, self._ui = dispatcher, provider, ui
        self._route = route_handler.active_route
        self._progress = 0
        self._generation = 0
        self._enabled = False
        self._layers = frozenset({"temperature", "rain", "wind"})
        self._forecasts = ()
        self._status = "Start a route to see weather along the way"
        self._busy = self._closed = False
        self._log = WeatherLog("weather.route")
        route_handler.observe_route(self._route_changed)
        presentation.observe_route_guidance(self._guidance_changed)

    def _route_changed(self, route):
        self._generation += 1
        self._route = route
        self._progress = 0
        self._forecasts = ()
        self.publish()
        self._status = "Start a route to see weather along the way" if route is None else "Route ready"
        self.publish()
        if self._enabled and route is not None:
            self.refresh()

    def _guidance_changed(self, message):
        data = message.data
        if data.route_complete:
            self._route_changed(None)
            return
        total = data.distance_along_route_m + data.distance_remaining_m
        self._progress = max(0, min(1, data.distance_along_route_m / total)) if total > 0 else 0

    def refresh(self):
        """Fetch the remaining route at estimated arrival times with one batch request."""
        if self._closed or not self._enabled or self._route is None:
            return
        if self._busy:
            return
        self._busy = True
        generation = self._generation
        route, progress = self._route, self._progress
        operation_id = self._log.requested()
        self._status = "Loading route forecast…"
        self.publish()

        def load():
            with operation(operation_id):
                try:
                    points = sample_route(route, datetime.now(timezone.utc), progress)
                    forecasts = self._provider.forecast(points)
                    error = None
                    self._log.succeeded(item_count=len(forecasts))
                except Exception as failure:
                    self._log.failed(failure)
                    forecasts, error = (), str(failure)
            if not self._closed:
                self._host.schedule_ui_callback(0, lambda: self._complete(generation, forecasts, error, operation_id))
            else:
                self._log.stale(operation_id)

        self._log.start(threading.Thread(target=load, name="route-weather", daemon=True), operation_id)

    def _complete(self, generation, forecasts, error, operation_id=None):
        self._busy = False
        if self._closed:
            self._log.stale(operation_id)
            return
        if generation != self._generation or not self._enabled:
            self._log.stale(operation_id)
            if self._enabled and self._route is not None:
                self.refresh()
            return
        if error:
            self._forecasts = ()
            self._status = f"Forecast unavailable: {error}"
        else:
            self._log.emit(logging.DEBUG, "overlay.applied", "Route weather result applied", operation_id, item_count=len(forecasts))
            self._forecasts = forecasts
            self._status = f"Updated {datetime.now().strftime('%I:%M %p').lstrip('0')} · Open-Meteo"
        self.publish()

    def set_enabled(self, enabled):
        """Enable route forecasts or clear the last route snapshot."""
        previous = self._enabled
        self._enabled = bool(enabled)
        if previous != self._enabled:
            self._log.changed("enabled", self._enabled, "overlay.visibility_changed", "Route weather visibility changed", enabled=self._enabled)
        self._generation += 1
        self._forecasts = ()
        self._status = "Route weather off" if not self._enabled else "Start a route to load forecasts"
        self.publish()
        if self._enabled:
            self.refresh()

    def set_layers(self, layers):
        """Choose checkpoint fields without another provider request."""
        if not set(layers) <= {"temperature", "rain", "wind"}:
            raise ValueError("Unknown route weather layer")
        self._layers = frozenset(layers)
        self.publish()

    def publish(self):
        """Emit a renderer-neutral checkpoint snapshot using normalized SI values."""
        if self._closed:
            return
        points = tuple(RouteWeatherPoint(
            GeoPoint(math.radians(f.checkpoint.point.latitude), math.radians(f.checkpoint.point.longitude)),
            f.checkpoint.arrival, f.temperature_c + 273.15 if f.temperature_c is not None else None,
            f.rain_probability / 100 if f.rain_probability is not None else None,
            f.wind_kmh / 3.6 if f.wind_kmh is not None else None, f.condition) for f in self._forecasts)
        self._ui.set_route_weather_state(RouteWeatherOverlayState(self._enabled, self._layers, self._status, points))

    def close(self):
        """Invalidate pending forecasts and close the provider connection pool."""
        self._closed = True
        self._generation += 1
        self._provider.close()
