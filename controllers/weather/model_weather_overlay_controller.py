# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Asynchronous full-area HRRR model overlays independent of radar playback."""

import logging

from datetime import datetime, timezone
import threading
from time import monotonic
from common.logging.structured import operation
from controllers.weather.weather_logging import WeatherLog

from controllers.weather.hrrr_map_layers import TEMPERATURE_COLORS, WIND_COLORS
from ui.ui_dispatcher_if import UiDispatcherIf
from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from ui.weather.weather_overlay_state import ModelWeatherOverlayState, WeatherColorStop, WeatherRaster
from controllers.weather.radar_palette import RadarPalette


class ModelWeatherOverlayController:
    """Load one selected model heatmap and expose its legend and readiness."""

    def __init__(self, dispatcher: UiDispatcherIf, tiles, provider, ui: WeatherOverlayUiIf):
        self._host, self._tiles, self._provider, self._ui = dispatcher, tiles, provider, ui
        self._loading = False
        self.kind = "off"
        self.status = "Select a weather overlay"
        self._frame = None
        self._generation = 0
        self._revision = 0
        self._busy = False
        self._closed = False
        self._log = WeatherLog("weather.model")

    def select(self, kind):
        """Select one heatmap; radar and route forecasts keep their own state."""
        if kind not in {"off", "temperature", "wind"}:
            raise ValueError("Unknown weather overlay")
        previous = self.kind
        self.kind = kind
        if previous != kind:
            self._log.changed("kind", kind, "overlay.selection_changed", "Model weather selection changed", kind=kind)
        self._loading = False
        self._generation += 1
        self._frame = None
        self.publish()
        self.status = "Weather overlay off" if kind == "off" else "Loading weather forecast…"
        self.publish()
        if kind != "off":
            self.refresh()

    def refresh(self):
        """Discover a recent forecast without blocking the UI or duplicating work."""
        if self._closed or self._busy or self.kind == "off":
            return
        self._busy = True
        generation, kind = self._generation, self.kind
        operation_id = self._log.requested()

        def load():
            with operation(operation_id):
                try:
                    frame, error = self._provider.get_frame(kind), None
                    self._log.succeeded()
                except Exception as failure:
                    self._log.failed(failure)
                    frame, error = None, str(failure)
            if not self._closed:
                self._host.schedule_ui_callback(0, lambda: self._complete(generation, frame, error, operation_id))
            else:
                self._log.stale(operation_id)

        self._log.start(threading.Thread(target=load, name="weather-model-overlay", daemon=True), operation_id)

    def _complete(self, generation, frame, error, operation_id=None):
        self._busy = False
        if self._closed:
            self._log.stale(operation_id)
            return
        if generation != self._generation:
            self._log.stale(operation_id)
            self.refresh()
            return
        if error:
            self._failed(error)
            return
        if (self._frame is None or self._frame.tile_url != frame.tile_url
                or self._tiles.frame_error(frame)):
            self._revision += 1
        self._frame = frame
        self._log.emit(logging.DEBUG, "overlay.applied", "Model weather result applied", operation_id)
        self._tiles.retry_frame(frame)
        self.publish()
        self._wait(generation, monotonic(), operation_id)

    def publish(self):
        """Present the selected raster and SI palette through the UI contract."""
        if self._closed:
            return
        frame = self._frame
        raster = None
        if frame is not None and self.kind != "off":
            raster = WeatherRaster(self._tiles.tile_url(frame, RadarPalette.UNIVERSAL) + f"?revision={self._revision}", frame.timestamp)
        palette = TEMPERATURE_COLORS if self.kind == "temperature" else WIND_COLORS if self.kind == "wind" else ()
        legend = tuple(WeatherColorStop(value + 273.15 if self.kind == "temperature" else value, rgb) for value, rgb in palette)
        self._ui.set_model_weather_state(ModelWeatherOverlayState(
            self.kind, self.status, raster, legend,
            datetime.fromtimestamp(frame.timestamp, timezone.utc) if frame else None, self._loading))

    def _wait(self, generation, started, operation_id=None):
        if self._closed or generation != self._generation or self._frame is None:
            return
        error = self._tiles.frame_error(self._frame)
        if error or monotonic() - started >= 180:
            self._log.failed(operation_id=operation_id, stage="tiles", reason="tile_error" if error else "timeout")
            self._failed(error or "Timed out waiting for map tiles; check renderer build and logs")
            return
        ready = self._tiles.frame_ready(self._frame)
        if ready:
            self._log.succeeded(operation_id, stage="tiles")
        self.status = "Weather forecast"
        self._loading = not ready
        self.publish()
        if not ready:
            self._host.schedule_ui_callback(300, lambda: self._wait(generation, started, operation_id))

    def _failed(self, error):
        self._loading = False
        self._frame = None
        self.publish()
        self.status = f"Model overlay unavailable: {error}"
        self.publish()

    def close(self):
        """Invalidate pending workers and release model discovery connections."""
        self._closed = True
        self._generation += 1
        self._provider.close()
