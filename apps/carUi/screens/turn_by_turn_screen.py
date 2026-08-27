# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI turn-by-turn navigation destination."""

from __future__ import annotations

import tkinter as tk

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from messaging.contracts.route_guidance import RouteGuidanceStateMessage
from ui.screen_ui_if import ScreenId

_METERS_PER_MILE = 1609.344


class TurnByTurnScreen(CarUiScreen):
    """Render the latest route-guidance message as a glanceable driving view."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
    ) -> None:
        super().__init__(host, ScreenId("turn_by_turn"), create_menu_tile)
        self._back_action = back_action
        self._latest: RouteGuidanceStateMessage | None = None
        self._distance_label: tk.Label | None = None
        self._instruction_label: tk.Label | None = None
        self._remaining_label: tk.Label | None = None

    def show(self) -> None:
        self.prepare_screen("Navigation", self._back_action)
        frame = tk.Frame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=28, pady=18)

        self._distance_label = tk.Label(frame, font=("TkDefaultFont", 30, "bold"))
        self._distance_label.pack(anchor="w")
        self._instruction_label = tk.Label(
            frame,
            font=("TkDefaultFont", 24, "bold"),
            justify="left",
            anchor="w",
            wraplength=850,
        )
        self._instruction_label.pack(fill="x", pady=(12, 18))
        self._remaining_label = tk.Label(frame, font=("TkDefaultFont", 15))
        self._remaining_label.pack(anchor="w")
        self._render_latest()

    def hide(self) -> None:
        self._distance_label = None
        self._instruction_label = None
        self._remaining_label = None

    def set_guidance_message(self, message: RouteGuidanceStateMessage) -> None:
        self._latest = message
        self._render_latest()

    def set_guidance_error(self, topic: str, error: Exception) -> None:
        self.set_status(f"Navigation guidance unavailable: {error}")

    def _render_latest(self) -> None:
        distance_label = self._distance_label
        instruction_label = self._instruction_label
        remaining_label = self._remaining_label
        if distance_label is None or instruction_label is None or remaining_label is None:
            return

        message = self._latest
        if message is None:
            distance_label.config(text="--")
            instruction_label.config(text="Waiting for route guidance")
            remaining_label.config(text="")
            self.set_status("No active route")
            return

        data = message.data
        if data.route_complete:
            distance_label.config(text="ARRIVED")
            instruction_label.config(text="Destination reached")
            remaining_label.config(text="")
            self.set_status("Route complete")
            return

        distance_label.config(text=_format_distance(data.distance_to_maneuver_m))
        instruction_label.config(text=data.instruction or "Continue on route")
        remaining_label.config(
            text=f"{data.distance_remaining_m / _METERS_PER_MILE:.1f} mi remaining"
        )
        self.set_status("Off route - recalculating" if data.off_route else "Guidance active")


def _format_distance(distance_m: float | None) -> str:
    if distance_m is None:
        return "--"
    if distance_m >= _METERS_PER_MILE:
        return f"{distance_m / _METERS_PER_MILE:.1f} mi"
    if distance_m >= 160.0:
        return f"{distance_m / 160.9344:.1f} tenths mi"
    return f"{distance_m:.0f} m"
