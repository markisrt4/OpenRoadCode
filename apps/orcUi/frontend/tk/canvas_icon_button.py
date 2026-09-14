# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Portable canvas-drawn icon controls for Tk frontends."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle


class CanvasIconButton(tk.Canvas):
    """Small icon-only control that does not depend on Unicode glyph support."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        icon: str,
        command: Callable[[], None],
        width: int = 40,
        height: int = 34,
    ) -> None:
        self._theme = theme
        self._icon = icon
        self._command = command
        self._pressed = False
        self._hovered = False
        ui = theme.ui
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=ui.control_background,
            highlightthickness=1,
            highlightbackground=ui.border,
            bd=0,
            cursor="hand2",
        )
        self._width = width
        self._height = height
        self.bind("<Enter>", self._on_enter)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Leave>", self._on_leave)
        self._paint()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._paint()

    def _on_press(self, _event: tk.Event) -> None:
        self._pressed = True
        self._paint()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._paint()
        if (
            was_pressed
            and 0 <= event.x <= self._width
            and 0 <= event.y <= self._height
        ):
            self._command()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._paint()

    def _paint(self) -> None:
        ui = self._theme.ui
        background = (
            ui.control_active
            if self._pressed
            else ui.surface_alt if self._hovered
            else ui.control_background
        )
        border = ui.accent_danger if self._icon == "power" and self._hovered else ui.border
        self.configure(bg=background, highlightbackground=border)
        self.delete("all")
        if self._icon == "power":
            self._draw_power(
                ui.accent_danger if self._hovered or self._pressed else ui.control_text
            )
        elif self._icon == "external":
            self._draw_external(ui.control_text)
        else:
            raise ValueError(f"Unsupported canvas icon: {self._icon}")

    def _draw_power(self, color: str) -> None:
        cx = self._width / 2
        cy = self._height / 2 + 2
        radius = min(self._width, self._height) * 0.29
        self.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=38,
            extent=284,
            style=tk.ARC,
            outline=color,
            width=3,
        )
        stem_top = cy - radius - 5
        stem_bottom = cy - 1
        self.create_line(
            cx,
            stem_top,
            cx,
            stem_bottom,
            fill=color,
            width=4,
            capstyle=tk.ROUND,
        )
        self.create_oval(
            cx - 2,
            stem_top - 2,
            cx + 2,
            stem_top + 2,
            fill=color,
            outline=color,
        )

    def _draw_external(self, color: str) -> None:
        left = self._width * 0.25
        top = self._height * 0.36
        right = self._width * 0.68
        bottom = self._height * 0.76
        self.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=color,
            width=2,
        )
        start_x = self._width * 0.48
        start_y = self._height * 0.53
        end_x = self._width * 0.76
        end_y = self._height * 0.24
        self.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill=color,
            width=2,
            arrow=tk.LAST,
            arrowshape=(8, 10, 4),
        )
        self.create_line(
            self._width * 0.59,
            self._height * 0.24,
            end_x,
            end_y,
            fill=color,
            width=2,
        )
        self.create_line(
            end_x,
            end_y,
            end_x,
            self._height * 0.41,
            fill=color,
            width=2,
        )
