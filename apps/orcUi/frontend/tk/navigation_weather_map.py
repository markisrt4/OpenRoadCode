# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Asynchronous full-area HRRR model overlays independent of radar playback."""

from datetime import datetime
import threading
from time import monotonic

from controllers.weather.hrrr_map_layers import HrrrMapLayerProvider, TEMPERATURE_COLORS, WIND_COLORS
from controllers.weather.radar_palette import RadarPalette


class NavigationWeatherMap:
    """Load one selected model heatmap and expose its legend and readiness."""

    def __init__(self, host, renderer, tiles, unit_system):
        self._host, self._renderer, self._tiles = host, renderer, tiles
        self._unit_system = unit_system
        self._provider = HrrrMapLayerProvider()
        self.kind = "off"
        self.status = "Select a model overlay · HRRR CONUS"
        self._frame = None
        self._generation = 0
        self._revision = 0
        self._busy = False
        self._closed = False
        self.on_changed = lambda: None

    def select(self, kind):
        """Select one heatmap; radar and route forecasts keep their own state."""
        if kind not in {"off", "temperature", "wind"}:
            raise ValueError("Unknown weather overlay")
        self.kind = kind
        self._generation += 1
        self._frame = None
        self._renderer.set_weather_field(None, enabled=False)
        self.status = "Model overlay off" if kind == "off" else "Loading HRRR model…"
        self.on_changed()
        if kind != "off":
            self.refresh()

    def refresh(self):
        """Discover a recent forecast without blocking the UI or duplicating work."""
        if self._closed or self._busy or self.kind == "off":
            return
        self._busy = True
        generation, kind = self._generation, self.kind

        def load():
            try:
                frame, error = self._provider.get_frame(kind), None
            except Exception as failure:
                frame, error = None, str(failure)
            if not self._closed:
                self._host.schedule_ui_callback(0, lambda: self._complete(generation, frame, error))

        threading.Thread(target=load, name="weather-model-overlay", daemon=True).start()

    def _complete(self, generation, frame, error):
        self._busy = False
        if self._closed:
            return
        if generation != self._generation:
            self.refresh()
            return
        if error:
            self._failed(error)
            return
        if (self._frame is None or self._frame.tile_url != frame.tile_url
                or self._tiles.frame_error(frame)):
            self._revision += 1
        self._frame = frame
        self._tiles.retry_frame(frame)
        self.publish()
        self._wait(generation, monotonic())

    def publish(self):
        """Replay the selected layer when the embedded renderer restarts."""
        if not self._closed and self._frame is not None and self.kind != "off":
            self._renderer.set_weather_field(self._tiles.tile_url(self._frame, RadarPalette.UNIVERSAL) + f"?revision={self._revision}",
                                             frame_time=self._frame.timestamp, max_zoom=9, opacity=0.45)

    def _wait(self, generation, started):
        if self._closed or generation != self._generation or self._frame is None:
            return
        error = self._tiles.frame_error(self._frame)
        if error or monotonic() - started >= 180:
            self._failed(error or "Timed out waiting for map tiles; check renderer build and logs")
            return
        valid = datetime.fromtimestamp(self._frame.timestamp).astimezone().strftime('%I:%M %p').lstrip('0')
        ready = self._tiles.frame_ready(self._frame)
        self.status = f"HRRR forecast · valid {valid} · CONUS" + ("" if ready else " · Loading tiles…")
        self.on_changed()
        if not ready:
            self._host.schedule_ui_callback(300, lambda: self._wait(generation, started))

    def _failed(self, error):
        self._frame = None
        self._renderer.set_weather_field(None, enabled=False)
        self.status = f"Model overlay unavailable: {error}"
        self.on_changed()

    def legend(self):
        """Return palette stops in the user's chosen temperature and speed units."""
        imperial = self._unit_system().value == "imperial"
        if self.kind == "temperature":
            return tuple((f"{value * 9 / 5 + 32:.0f}°F" if imperial else f"{value:g}°C", rgb)
                         for value, rgb in TEMPERATURE_COLORS)
        if self.kind == "wind":
            return tuple((f"{value * 2.236936:.0f} mph" if imperial else f"{value * 3.6:g} km/h", rgb)
                         for value, rgb in WIND_COLORS)
        return ()

    def close(self):
        """Invalidate pending workers and release model discovery connections."""
        self._closed = True
        self._generation += 1
        self._provider.close()
