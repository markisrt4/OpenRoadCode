# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt lighting controllers to toolkit-independent lighting UI contracts."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import LightingConnectionStatus, RgbColor
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
        self._backend = backend
        self._lighting_ui = lighting_ui
        self._dispatch = dispatch

    def connect(self) -> None:
        self.refresh()
        self._submit(self._backend.connect(), "Lighting connected")

    def refresh(self, status_message: str | None = None) -> LightingState:
        source = self._backend.current_state()
        derived_status, error_message = self._connection_messages(source.connection_status, source.last_connection_error)
        state = LightingState(
            connected=source.connected,
            power_enabled=source.power_enabled,
            color=LightingColor(source.color.red, source.color.green, source.color.blue),
            brightness_percent=source.brightness_percent,
            pattern_index=source.pattern_index,
            music_mode=source.music_mode,
            status_message=status_message or derived_status,
            error_message=error_message,
        )
        self._lighting_ui.set_lighting_state(state)
        return state

    def request_power(self, enabled: bool) -> None:
        self._submit(self._backend.set_power(enabled), "Lighting on" if enabled else "Lighting off")

    def request_color(self, color: LightingColor) -> None:
        self._submit(
            self._backend.set_color(RgbColor(color.red, color.green, color.blue)),
            "Lighting color changed",
        )

    def request_brightness(self, percent: int) -> None:
        self._submit(self._backend.set_brightness(percent), f"Brightness: {percent}%")

    def request_pattern(self, pattern_index: int) -> None:
        self._submit(self._backend.set_pattern(pattern_index), "Lighting effect changed")

    def request_music_mode(self, mode_index: int) -> None:
        self._submit(self._backend.set_music_mode(mode_index), "Lighting music mode changed")

    def _submit(self, future: Future[None], success_message: str) -> None:
        future.add_done_callback(
            lambda completed: self._dispatch(lambda: self._complete(completed, success_message))
        )

    def _complete(self, future: Future[None], success_message: str) -> None:
        try:
            future.result()
        except Exception as exc:
            # Refresh first so transport state/address/error remain visible, then
            # overlay the operation failure for the presentation boundary.
            state = self.refresh()
            self._lighting_ui.set_lighting_state(
                LightingState(
                    connected=state.connected,
                    power_enabled=state.power_enabled,
                    color=state.color,
                    brightness_percent=state.brightness_percent,
                    pattern_index=state.pattern_index,
                    music_mode=state.music_mode,
                    status_message=state.status_message,
                    error_message=f"Lighting error: {exc}",
                )
            )
        else:
            self.refresh(success_message)

    @staticmethod
    def _connection_messages(
        status: LightingConnectionStatus,
        last_error: str | None,
    ) -> tuple[str, str | None]:
        if status is LightingConnectionStatus.CONNECTED:
            return "Lighting connected", None
        if status is LightingConnectionStatus.CONNECTING:
            return "Connecting to lighting…", None
        if status is LightingConnectionStatus.RECONNECTING:
            return "Reconnecting to lighting…", None
        if status is LightingConnectionStatus.ERROR:
            return "Lighting connection error", last_error or "Lighting connection failed"
        return "Lighting disconnected", None
