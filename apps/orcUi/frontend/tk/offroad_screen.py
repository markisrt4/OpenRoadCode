# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Off-road screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

import math
from collections.abc import Callable

from apps.orcUi.frontend.tk.presentation_state import OrcUiPresentationState
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from frontends.tk.automotive import OffroadDashboardPanel
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation import HeadingReference, PositionFix
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle


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
        self._panel: OffroadDashboardPanel | None = None

    def show(self) -> None:
        """Build OFF-ROAD content from the latest navigation state."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("OFF-ROAD")
        self._host.set_screen_back_action(self._on_back)
        panel = OffroadDashboardPanel(
            self._host.screen_parent,
            pitch_warning_deg=30.0,
            roll_warning_deg=25.0,
            request_handler=None,
        )
        panel.set_style_sheet(self._theme_bundle().style_sheet)
        panel.pack(fill="both", expand=True)
        self._panel = panel
        self._apply_navigation_state()

    def hide(self) -> None:
        self._panel = None

    def apply_position_state(self, state: PositionPresentationState) -> None:
        self._apply_navigation_state()

    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        self._apply_navigation_state()

    def _apply_navigation_state(self) -> None:
        panel = self._panel
        if panel is None or not panel.winfo_exists():
            return
        attitude = self._presentation.attitude
        panel.set_heading(
            None if attitude.heading_deg is None else math.radians(attitude.heading_deg),
            HeadingReference.RELATIVE,
        )
        panel.set_pitch(None if attitude.pitch_deg is None else math.radians(attitude.pitch_deg))
        panel.set_roll(None if attitude.roll_deg is None else math.radians(attitude.roll_deg))
        position = self._presentation.position
        if position.latitude_deg is None or position.longitude_deg is None:
            panel.set_position(None)
            return
        panel.set_position(
            PositionFix(
                latitude_rad=math.radians(position.latitude_deg),
                longitude_rad=math.radians(position.longitude_deg),
                altitude_m=(
                    None
                    if position.altitude_ft is None
                    else position.altitude_ft / 3.280839895013123
                ),
                pfom_m=position.accuracy_m,
            )
        )
