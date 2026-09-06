# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI turn-by-turn navigation destination."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation.route_guidance_ui_if import RouteGuidanceUiIf
from ui.screen_ui_if import ScreenId

_METERS_PER_MILE = 1609.344


class TurnByTurnScreen(CarUiScreen, RouteGuidanceUiIf):
    """Render toolkit-neutral route-guidance presentation state."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
    ) -> None:
        super().__init__(host, ScreenId("turn_by_turn"), create_menu_tile)
        self._back_action = back_action
        self._instruction: str | None = None
        self._distance_to_maneuver_m: float | None = None
        self._distance_remaining_m: float | None = None
        self._off_route = False
        self._route_complete = False
        self._simulation_action: Callable[[], None] | None = None
        self._distance_label: tk.Label | None = None
        self._instruction_label: tk.Label | None = None
        self._remaining_label: tk.Label | None = None

    def set_simulation_action(self, action: Callable[[], None]) -> None:
        """Install the temporary development action for route simulation."""
        self._simulation_action = action

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

        if self._simulation_action is not None:
            tk.Button(
                frame,
                text="SIMULATE ROUTE 60x",
                command=self._simulation_action,
                padx=18,
                pady=10,
            ).pack(anchor="e", side="bottom", pady=(14, 0))

        self._render()

    def hide(self) -> None:
        self._distance_label = None
        self._instruction_label = None
        self._remaining_label = None

    def set_instruction(self, instruction: str | None) -> None:
        self._instruction = instruction
        self._render()

    def set_distance_to_maneuver(self, distance_m: float | None) -> None:
        self._distance_to_maneuver_m = distance_m
        self._render()

    def set_distance_remaining(self, distance_m: float | None) -> None:
        self._distance_remaining_m = distance_m
        self._render()

    def set_off_route(self, off_route: bool) -> None:
        self._off_route = off_route
        self._render()

    def set_route_complete(self, complete: bool) -> None:
        self._route_complete = complete
        self._render()

    def _render(self) -> None:
        distance_label = self._distance_label
        instruction_label = self._instruction_label
        remaining_label = self._remaining_label
        if distance_label is None or instruction_label is None or remaining_label is None:
            return

        if self._route_complete:
            distance_label.config(text="ARRIVED")
            instruction_label.config(text="Destination reached")
            remaining_label.config(text="")
            self.set_status("Route complete")
            return

        distance_label.config(text=_format_distance(self._distance_to_maneuver_m))
        instruction_label.config(text=self._instruction or "Waiting for route guidance")
        if self._distance_remaining_m is None:
            remaining_label.config(text="")
        else:
            remaining_label.config(
                text=f"{self._distance_remaining_m / _METERS_PER_MILE:.1f} mi remaining"
            )
        self.set_status("Off route - recalculating" if self._off_route else "Guidance active")


def _format_distance(distance_m: float | None) -> str:
    if distance_m is None:
        return "--"
    if distance_m >= _METERS_PER_MILE:
        return f"{distance_m / _METERS_PER_MILE:.1f} mi"
    if distance_m >= 160.0:
        return f"{distance_m / 160.9344:.1f} tenths mi"
    return f"{distance_m:.0f} m"
