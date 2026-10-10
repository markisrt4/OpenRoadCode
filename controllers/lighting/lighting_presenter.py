# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt lighting controllers to toolkit-independent lighting UI contracts."""

from __future__ import annotations

from collections.abc import Callable

from common.logging.diagnostics import ComponentLog, diagnostic_action
from common.logging.structured import current_operation
from concurrent.futures import Future

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import RgbColor
from ui.lighting import (
    LightingColor,
    LightingRequestHandlerIf,
    LightingState,
    LightingUiIf,
)


class LightingPresenter(LightingRequestHandlerIf):
    """Publish lighting state and handle requests without toolkit coupling."""

    def __init__(
        self,
        backend: LightingControllerIf,
        lighting_ui: LightingUiIf,
        dispatch: Callable[[Callable[[], None]], None],
    ) -> None:
        self._diagnostics = ComponentLog("lighting.ui", "lighting")
        self._backend = backend
        self._lighting_ui = lighting_ui
        self._dispatch = dispatch

    @diagnostic_action("connect")
    def connect(self) -> None:
        self._submit(self._backend.connect(), "Lighting connected")

    def refresh(self, status_message: str | None = None) -> LightingState:
        source = self._backend.current_state()
        state = LightingState(
            connected=source.connected,
            power_enabled=source.power_enabled,
            color=LightingColor(
                source.color.red,
                source.color.green,
                source.color.blue,
            ),
            brightness_percent=source.brightness_percent,
            pattern_index=source.pattern_index,
            music_mode=source.music_mode,
            status_message=status_message,
        )
        self._diagnostics.changed("connection", state.connected)
        self._lighting_ui.set_lighting_state(state)
        return state

    @diagnostic_action("request_power")
    def request_power(self, enabled: bool) -> None:
        self._submit(
            self._backend.set_power(enabled),
            "Lighting on" if enabled else "Lighting off",
        )

    @diagnostic_action("request_color")
    def request_color(self, color: LightingColor) -> None:
        self._submit(
            self._backend.set_color(RgbColor(color.red, color.green, color.blue)),
            "Lighting color changed",
        )

    @diagnostic_action("request_brightness")
    def request_brightness(self, percent: int) -> None:
        self._submit(
            self._backend.set_brightness(percent),
            f"Brightness: {percent}%",
        )

    @diagnostic_action("request_pattern")
    def request_pattern(self, pattern_index: int) -> None:
        self._submit(
            self._backend.set_pattern(pattern_index),
            "Lighting effect changed",
        )

    @diagnostic_action("request_music_mode")
    def request_music_mode(self, mode_index: int) -> None:
        self._submit(
            self._backend.set_music_mode(mode_index),
            "Lighting music mode changed",
        )

    def _submit(self, future: Future[None], success_message: str) -> None:
        operation_id = current_operation()
        future.add_done_callback(
            lambda completed: self._dispatch(
                lambda: self._complete(completed, success_message, operation_id)
            )
        )

    def _complete(self, future: Future[None], success_message: str, operation_id=None) -> None:
        try:
            future.result()
        except Exception as exc:
            self._diagnostics.failed("completion", exc, operation_id)
            self._lighting_ui.set_lighting_state(
                LightingState(error_message=f"Lighting error: {exc}")
            )
        else:
            self._diagnostics.succeeded("completion", operation_id)
            self.refresh(success_message)
