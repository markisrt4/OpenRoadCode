# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact off-road roll and pitch indicators."""

from __future__ import annotations

import math
import tkinter as tk

from ui.theme import ThemeBundle
from .shell_metrics import FONT_SMALL


class RollIndicator(tk.Canvas):
    """Automotive-style lateral tilt indicator."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        self._value: float | None = None
        super().__init__(
            parent,
            height=74,
            bg=theme.ui.surface,
            highlightthickness=0,
            bd=0,
        )
        self.bind("<Configure>", lambda _event: self._paint())

    def set_value(self, value: float | None) -> None:
        self._value = value
        self._paint()

    def _paint(self) -> None:
        ui = self._theme.ui
        self.delete("all")
        width = max(120, self.winfo_width())
        height = max(70, self.winfo_height())
        cx = width / 2
        cy = height * 0.58
        span = min(width * 0.34, 72)
        self.create_arc(
            cx - span,
            cy - span,
            cx + span,
            cy + span,
            start=25,
            extent=130,
            style=tk.ARC,
            outline=ui.border,
            width=2,
        )
        for degrees in (-30, -15, 0, 15, 30):
            angle = math.radians(90 - degrees)
            inner = span - 6
            outer = span + (3 if degrees == 0 else 0)
            x1 = cx + inner * math.cos(angle)
            y1 = cy - inner * math.sin(angle)
            x2 = cx + outer * math.cos(angle)
            y2 = cy - outer * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=ui.text_muted, width=2)

        value = 0.0 if self._value is None else max(-35.0, min(35.0, self._value))
        angle = math.radians(value)
        half = span * 0.62
        dx = half * math.cos(angle)
        dy = half * math.sin(angle)
        color = (
            ui.text_muted
            if self._value is None
            else ui.accent_danger if abs(value) >= 20.0 else ui.accent_primary
        )
        self.create_line(
            cx - dx,
            cy + dy,
            cx + dx,
            cy - dy,
            fill=color,
            width=4,
        )
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color, outline="")
        label = "--" if self._value is None else f"{self._value:+.1f}°"
        self.create_text(
            cx,
            height - 7,
            text=label,
            fill=ui.text,
            font=("Sans", FONT_SMALL, "bold"),
        )


class PitchIndicator(tk.Canvas):
    """Vertical incline indicator with a centered zero datum."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        self._value: float | None = None
        super().__init__(
            parent,
            height=74,
            bg=theme.ui.surface,
            highlightthickness=0,
            bd=0,
        )
        self.bind("<Configure>", lambda _event: self._paint())

    def set_value(self, value: float | None) -> None:
        self._value = value
        self._paint()

    def _paint(self) -> None:
        ui = self._theme.ui
        self.delete("all")
        width = max(120, self.winfo_width())
        height = max(70, self.winfo_height())
        cx = width / 2
        top = 8
        bottom = height - 20
        cy = (top + bottom) / 2
        self.create_line(cx, top, cx, bottom, fill=ui.border, width=3)
        for degrees in (-20, -10, 0, 10, 20):
            y = cy - (degrees / 20.0) * ((bottom - top) * 0.42)
            tick = 13 if degrees == 0 else 8
            self.create_line(cx - tick, y, cx + tick, y, fill=ui.text_muted, width=2)

        value = 0.0 if self._value is None else max(-25.0, min(25.0, self._value))
        y = cy - (value / 25.0) * ((bottom - top) * 0.45)
        color = (
            ui.text_muted
            if self._value is None
            else ui.accent_danger if abs(value) >= 20.0 else ui.accent_success
        )
        self.create_polygon(
            cx - 16,
            y,
            cx - 7,
            y - 6,
            cx - 7,
            y + 6,
            fill=color,
            outline=color,
        )
        self.create_polygon(
            cx + 16,
            y,
            cx + 7,
            y - 6,
            cx + 7,
            y + 6,
            fill=color,
            outline=color,
        )
        label = "--" if self._value is None else f"{self._value:+.1f}°"
        self.create_text(
            cx,
            height - 7,
            text=label,
            fill=ui.text,
            font=("Sans", FONT_SMALL, "bold"),
        )
