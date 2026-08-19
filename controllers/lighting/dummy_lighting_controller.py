# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from concurrent.futures import Future
from threading import Lock

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import (
    CustomPatternMode,
    LightingConnectionStatus,
    LightingState,
    RgbColor,
)


class DummyLightingController(LightingControllerIf):
    """Stateful no-hardware lighting controller for development and tests."""

    def __init__(
        self,
        initial_state: LightingState | None = None,
    ) -> None:
        self._state = initial_state or LightingState()
        self._closed = False
        self._lock = Lock()

    @property
    def is_connected(self) -> bool:
        return self.current_state().connected

    def current_state(self) -> LightingState:
        with self._lock:
            return self._state

    def connect(self) -> Future[None]:
        return self._update(connection_status=LightingConnectionStatus.CONNECTED)

    def disconnect(self) -> Future[None]:
        if self._closed:
            return self._failed(RuntimeError("lighting controller is closed"))
        return self._update(connection_status=LightingConnectionStatus.DISCONNECTED)

    def close(self) -> None:
        with self._lock:
            self._state = self._state.updated(
                connection_status=LightingConnectionStatus.DISCONNECTED
            )
            self._closed = True

    def set_power(self, enabled: bool) -> Future[None]:
        return self._update(power_enabled=bool(enabled))

    def set_color(self, color: RgbColor) -> Future[None]:
        return self._update(color=color)

    def set_brightness(self, percent: int) -> Future[None]:
        _validate_range("percent", percent, 0, 100)
        return self._update(brightness_percent=percent)

    def set_color_temperature(self, percent: int) -> Future[None]:
        _validate_range("percent", percent, 0, 100)
        return self._update(color_temperature_percent=percent)

    def set_pattern(self, pattern_index: int) -> Future[None]:
        _validate_range("pattern_index", pattern_index, 0, 210)
        return self._update(pattern_index=pattern_index)

    def set_music_mode(self, eq_mode: int) -> Future[None]:
        _validate_range("eq_mode", eq_mode, 0, 255)
        return self._update(music_mode=eq_mode)

    def set_custom_pattern_mode(self, mode: CustomPatternMode) -> Future[None]:
        return self._update(custom_pattern_mode=mode)

    def set_custom_pattern_direction(self, is_forward: bool) -> Future[None]:
        return self._update(custom_pattern_forward=bool(is_forward))

    def _update(self, **changes: object) -> Future[None]:
        with self._lock:
            if self._closed:
                return self._failed(RuntimeError("lighting controller is closed"))
            self._state = self._state.updated(**changes)
        return self._done()

    @staticmethod
    def _done() -> Future[None]:
        future: Future[None] = Future()
        future.set_result(None)
        return future

    @staticmethod
    def _failed(exc: Exception) -> Future[None]:
        future: Future[None] = Future()
        future.set_exception(exc)
        return future


def _validate_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in range {minimum}..{maximum}")
