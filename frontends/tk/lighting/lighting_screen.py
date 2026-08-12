# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk screen for lighting controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from frontends.tk.lighting.lighting_controls_panel import LightingControlsPanel
from frontends.tk import TkScreen, TkScreenHostIf
from ui.lighting import LightingRequestHandlerIf, LightingState, LightingUiIf
from ui.screen_ui_if import ScreenId


class LightingScreen(TkScreen, LightingUiIf):
    """Present lighting state and connect lighting request handling."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme: dict[str, Any],
        back_action: Callable[[], None],
    ) -> None:
        super().__init__(ScreenId("lighting"))
        self._host = host
        self._theme = theme
        self._back_action = back_action
        self._state: LightingState | None = None
        self._handler: LightingRequestHandlerIf | None = None
        self._activation_callback: Callable[[], None] | None = None
        self.lighting_panel: LightingControlsPanel | None = None

    def set_lighting_state(self, state: LightingState | None) -> None:
        self._state = state
        if self.lighting_panel is not None:
            self.lighting_panel.set_lighting_state(state)

    def set_lighting_request_handler(
        self,
        handler: LightingRequestHandlerIf | None,
    ) -> None:
        self._handler = handler
        if self.lighting_panel is not None:
            self.lighting_panel.set_lighting_request_handler(handler)

    def set_activation_callback(
        self,
        callback: Callable[[], None] | None,
    ) -> None:
        self._activation_callback = callback

    def show(self) -> None:
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Lighting Controls")
        self._host.set_screen_back_action(self._back_action)

        panel = LightingControlsPanel(
            parent=self._host.screen_parent,
            theme=self._theme,
        )
        panel.set_lighting_request_handler(self._handler)
        panel.set_lighting_state(self._state)
        panel.pack(fill="both", expand=True)
        self.lighting_panel = panel

        if self._activation_callback is not None:
            self._activation_callback()
        self._host.set_screen_status("Lighting controls ready")
