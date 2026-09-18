# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Off-road screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.frontend.tk.presentation_state import OrcUiPresentationState
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

from .offroad_panel import OffRoadPanel
from .screen_builders import build_offroad_screen


class OffRoadScreen(TkScreen):
    """Own the standalone OFF-ROAD context destination."""

    SCREEN_ID = ScreenId("OFF-ROAD")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        presentation: OrcUiPresentationState,
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._theme_bundle = theme_bundle
        self._presentation = presentation
        self._on_back = on_back
        self._panel: OffRoadPanel | None = None

    def show(self) -> None:
        """Build OFF-ROAD content from the latest navigation state."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("OFF-ROAD")
        self._panel = build_offroad_screen(
            self._host.screen_parent,
            on_back=self._on_back,
            position=self._presentation.position,
            attitude=self._presentation.attitude,
            theme=self._theme_bundle(),
        )

    def hide(self) -> None:
        self._panel = None

    def apply_position_state(self, state: PositionPresentationState) -> None:
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_position(state)

    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_attitude(state)
