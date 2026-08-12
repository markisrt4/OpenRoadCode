# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk system-volume controls and indicator."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from frontends.tk.system.volume_indicator import (
    VolumeIndicator,
    VolumeIndicatorStyle,
)
from ui.system import VolumeRequestHandlerIf, VolumeUiIf


class VolumePanel(tk.Frame, VolumeUiIf):
    """Display normalized system volume and emit semantic volume requests."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        theme: dict[str, Any],
        compact_ui: bool,
        indicator_steps: int,
    ) -> None:
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"][
            "compact" if compact_ui else "normal"
        ]
        self._indicator_steps = max(1, indicator_steps)
        self._muted: bool | None = None
        self._handler: VolumeRequestHandlerIf | None = None

        super().__init__(parent, bg=self._colors["background"])
        self._build()

    def set_volume(self, volume_percent: float | None) -> None:
        if volume_percent is None:
            level = 0
        else:
            clamped = max(0.0, min(100.0, volume_percent))
            level = round(clamped * self._indicator_steps / 100.0)
        self._indicator.set_level(level)

    def set_muted(self, muted: bool | None) -> None:
        self._muted = muted
        self._indicator.set_muted(muted is True)

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        self._handler = handler

    def _request_volume_up(self) -> None:
        if self._handler is not None:
            self._handler.request_volume_up()

    def _request_volume_down(self) -> None:
        if self._handler is not None:
            self._handler.request_volume_down()

    def _request_mute_toggle(self, _event: tk.Event) -> None:
        if self._handler is not None:
            self._handler.request_mute(not bool(self._muted))

    def _build(self) -> None:
        down_button = self._button(
            self._layout["volume_down_text"],
            self._request_volume_down,
        )
        down_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["volume_button_gap"]),
        )

        self._indicator = VolumeIndicator(
            self,
            steps=self._indicator_steps,
            initial_level=0,
            initial_muted=False,
            style=VolumeIndicatorStyle(
                background=self._colors["background"],
                active=self._colors["volume_indicator_active"],
                inactive=self._colors["volume_indicator_inactive"],
                muted=self._colors["volume_indicator_muted"],
                bar_width=self._style["volume_bar_width"],
                base_height=self._style["volume_bar_base_height"],
                height_step=self._style["volume_bar_height_step"],
                bar_gap=self._style["volume_bar_gap"],
                anchor=self._layout["bottom_anchor"],
                side=self._layout["left_side"],
            ),
        )
        self._indicator.pack(
            side=self._layout["left_side"],
            padx=(
                self._style["indicator_left_gap"],
                self._style["indicator_right_gap"],
            ),
        )
        self._indicator.bind("<Button-1>", self._request_mute_toggle)

        up_button = self._button(
            self._layout["volume_up_text"],
            self._request_volume_up,
        )
        up_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["settings_gap"]),
        )

    def _button(self, text: str, command) -> tk.Button:
        return tk.Button(
            self,
            text=text,
            font=self._style["volume_button_font"],
            bg=self._colors["volume_button_bg"],
            fg=self._colors["volume_button_fg"],
            activebackground=self._colors["active"],
            activeforeground=self._colors["volume_button_fg"],
            bd=self._layout["button_border_width"],
            width=self._style["volume_button_width"],
            height=self._layout["button_height"],
            cursor=self._layout["cursor"],
            command=command,
        )
