# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Rate-limit and coalesce music-reactive lighting hardware commands."""
from __future__ import annotations

import threading
import time

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import RgbColor

from .music_lighting_output import MusicLightingOutput


class MusicLightingOutputAdapter:
    """Translate fast music outputs into sane lighting-controller updates."""

    def __init__(
        self,
        controller: LightingControllerIf,
        *,
        max_updates_per_second: float = 10.0,
        color_threshold: int = 10,
        brightness_threshold_percent: int = 4,
    ) -> None:
        if max_updates_per_second <= 0:
            raise ValueError("max_updates_per_second must be positive")
        self._controller = controller
        self._interval = 1.0 / max_updates_per_second
        self._color_threshold = max(0, int(color_threshold))
        self._brightness_threshold = max(0, int(brightness_threshold_percent))
        self._lock = threading.RLock()
        self._pending: MusicLightingOutput | None = None
        self._last_color: RgbColor | None = None
        self._last_brightness: int | None = None
        self._last_sent_at = 0.0
        self._timer: threading.Timer | None = None
        self._enabled = False

    def set_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._pending = None
                timer = self._timer
                self._timer = None
            else:
                timer = None
        if timer is not None:
            timer.cancel()
        self._controller.set_power(enabled)

    def submit(self, output: MusicLightingOutput) -> None:
        with self._lock:
            if not self._enabled:
                return
            self._pending = output
            now = time.monotonic()
            delay = max(0.0, self._interval - (now - self._last_sent_at))
            if self._timer is not None:
                return
            if delay == 0.0:
                pending = self._pending
                self._pending = None
            else:
                self._timer = threading.Timer(delay, self._flush)
                self._timer.daemon = True
                self._timer.start()
                return
        if pending is not None:
            self._send(pending)

    def close(self) -> None:
        with self._lock:
            timer = self._timer
            self._timer = None
            self._pending = None
            self._enabled = False
        if timer is not None:
            timer.cancel()

    def _flush(self) -> None:
        with self._lock:
            self._timer = None
            if not self._enabled:
                self._pending = None
                return
            pending = self._pending
            self._pending = None
        if pending is not None:
            self._send(pending)
        with self._lock:
            if self._pending is not None and self._timer is None and self._enabled:
                self._timer = threading.Timer(self._interval, self._flush)
                self._timer.daemon = True
                self._timer.start()

    def _send(self, output: MusicLightingOutput) -> None:
        color = output.color
        brightness = round(output.brightness * 100)
        if self._color_changed(color):
            self._controller.set_color(color)
            self._last_color = color
        if self._last_brightness is None or abs(brightness - self._last_brightness) >= self._brightness_threshold:
            self._controller.set_brightness(brightness)
            self._last_brightness = brightness
        with self._lock:
            self._last_sent_at = time.monotonic()

    def _color_changed(self, color: RgbColor) -> bool:
        previous = self._last_color
        if previous is None:
            return True
        return max(
            abs(color.red - previous.red),
            abs(color.green - previous.green),
            abs(color.blue - previous.blue),
        ) >= self._color_threshold
