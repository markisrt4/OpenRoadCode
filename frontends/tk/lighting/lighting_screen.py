# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk screen for lighting controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import tkinter as tk

from frontends.tk import TkScreen, TkScreenHostIf
from frontends.tk.lighting.color_wheel import ColorWheel
from frontends.tk.lighting.lighting_controls_panel import LightingControlsPanel
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
        self.color_wheel: ColorWheel | None = None

    def set_lighting_state(self, state: LightingState | None) -> None:
        self._state = state
        if self.lighting_panel is not None:
            self.lighting_panel.set_lighting_state(state)
        if state is not None and self.color_wheel is not None:
            self.color_wheel.set_color(state.color)

    def set_lighting_request_handler(
        self,
        handler: LightingRequestHandlerIf | None,
    ) -> None:
        self._handler = handler
        if self.lighting_panel is not None:
            self.lighting_panel.set_lighting_request_handler(handler)
        if self.color_wheel is not None:
            self.color_wheel.set_color_request_handler(handler)

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

        container = tk.Frame(
            self._host.screen_parent,
            bg=self._theme["colors"]["background"],
        )
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        wheel_frame = tk.Frame(
            container,
            bg=self._theme["colors"]["card_background"],
            padx=12,
            pady=12,
            highlightbackground=self._theme["colors"]["card_border"],
            highlightthickness=1,
        )
        wheel_frame.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)

        tk.Label(
            wheel_frame,
            text="Color",
            bg=self._theme["colors"]["card_background"],
            fg=self._theme["colors"]["text"],
            font=self._theme["profiles"]["default"]["section_title_font"],
        ).pack(anchor="w", pady=(0, 8))

        wheel = ColorWheel(
            wheel_frame,
            diameter=220,
            background=self._theme["colors"]["card_background"],
        )
        wheel.set_color_request_handler(self._handler)
        if self._state is not None:
            wheel.set_color(self._state.color)
        wheel.pack()
        self.color_wheel = wheel

        panel = LightingControlsPanel(
            parent=container,
            theme=self._theme,
        )
        panel.set_lighting_request_handler(self._handler)
        panel.set_lighting_state(self._state)
        panel.grid(row=0, column=1, sticky="nsew")
        self.lighting_panel = panel

        if self._activation_callback is not None:
            self._activation_callback()
        self._host.set_screen_status("Lighting controls ready")
