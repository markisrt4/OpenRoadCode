# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vector trip metric card used by the ORC automotive dashboard."""

from __future__ import annotations

import math
import tkinter as tk


class TripMetricCard(tk.Canvas):
    """Dark metric card with a lightweight vector automotive icon."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        unit: str,
        icon: str,
        background: str,
        border: str,
        text: str,
        muted: str,
        accent: str,
    ) -> None:
        super().__init__(
            parent,
            bg=background,
            highlightthickness=1,
            highlightbackground=border,
            bd=0,
            relief=tk.FLAT,
        )
        self._title = title
        self._unit = unit
        self._icon = icon
        self._background = background
        self._border = border
        self._text = text
        self._muted = muted
        self._accent = accent
        self._value = "--"
        self._status_accent: str | None = None
        self.bind("<Configure>", self._redraw)

    def set_value(self, value: str, *, accent: str | None = None) -> None:
        if value == self._value and accent == self._status_accent:
            return
        self._value = value
        self._status_accent = accent
        self._redraw()

    def _redraw(self, _event=None) -> None:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.delete("all")

        icon_x = 48
        icon_y = height / 2.0
        icon_color = self._status_accent or self._accent
        self._draw_icon(self._icon, icon_x, icon_y, 25, icon_color)

        text_x = 90
        self.create_text(
            text_x,
            max(18, height * 0.25),
            text=self._title,
            fill=self._muted,
            font=("Sans", 9, "bold"),
            anchor="w",
        )
        self.create_text(
            text_x,
            height * 0.54,
            text=self._value,
            fill=self._status_accent or self._text,
            font=("Sans", 20, "bold"),
            anchor="w",
        )
        if self._unit:
            self.create_text(
                width - 14,
                height * 0.58,
                text=self._unit,
                fill=self._muted,
                font=("Sans", 8, "bold"),
                anchor="e",
            )

    def _draw_icon(
        self,
        icon: str,
        cx: float,
        cy: float,
        radius: float,
        color: str,
    ) -> None:
        drawing = getattr(self, f"_icon_{icon}", None)
        if drawing is None:
            drawing = self._icon_road
        drawing(cx, cy, radius, color)

    def _icon_status(self, cx, cy, r, color) -> None:
        self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=3)
        points = (cx-r*0.25, cy-r*0.45, cx-r*0.25, cy+r*0.45, cx+r*0.55, cy)
        self.create_polygon(points, fill=color, outline="")

    def _icon_pin(self, cx, cy, r, color) -> None:
        self.create_oval(cx-r*0.55, cy-r*0.78, cx+r*0.55, cy+r*0.30, outline=color, width=3)
        self.create_polygon(
            cx-r*0.42, cy+r*0.05,
            cx+r*0.42, cy+r*0.05,
            cx, cy+r,
            fill=color,
            outline=color,
        )
        self.create_oval(cx-r*0.18, cy-r*0.42, cx+r*0.18, cy-r*0.06, fill=color, outline="")

    def _icon_clock(self, cx, cy, r, color) -> None:
        self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=3)
        self.create_line(cx, cy, cx, cy-r*0.55, fill=color, width=3, capstyle=tk.ROUND)
        self.create_line(cx, cy, cx+r*0.48, cy+r*0.28, fill=color, width=3, capstyle=tk.ROUND)

    def _icon_wheel(self, cx, cy, r, color) -> None:
        self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=3)
        self.create_oval(cx-r*0.22, cy-r*0.22, cx+r*0.22, cy+r*0.22, outline=color, width=2)
        for angle in (-90, 30, 150):
            a = math.radians(angle)
            self.create_line(
                cx + math.cos(a)*r*0.2,
                cy + math.sin(a)*r*0.2,
                cx + math.cos(a)*r*0.82,
                cy + math.sin(a)*r*0.82,
                fill=color,
                width=3,
                capstyle=tk.ROUND,
            )

    def _icon_pause(self, cx, cy, r, color) -> None:
        self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=3)
        self.create_rectangle(cx-r*0.42, cy-r*0.46, cx-r*0.12, cy+r*0.46, fill=color, outline="")
        self.create_rectangle(cx+r*0.12, cy-r*0.46, cx+r*0.42, cy+r*0.46, fill=color, outline="")

    def _icon_speed(self, cx, cy, r, color) -> None:
        self.create_arc(
            cx-r,
            cy-r,
            cx+r,
            cy+r,
            start=20,
            extent=140,
            style=tk.ARC,
            outline=color,
            width=4,
        )
        self.create_line(cx, cy, cx+r*0.56, cy-r*0.42, fill=color, width=3, capstyle=tk.ROUND)
        self.create_oval(cx-3, cy-3, cx+3, cy+3, fill=color, outline="")

    def _icon_fuel(self, cx, cy, r, color) -> None:
        left = cx-r*0.65
        top = cy-r*0.72
        self.create_rectangle(left, top, cx+r*0.18, cy+r*0.72, outline=color, width=3)
        self.create_rectangle(left+r*0.16, top+r*0.16, cx, cy-r*0.25, outline=color, width=2)
        self.create_line(cx+r*0.18, cy-r*0.45, cx+r*0.55, cy-r*0.18, fill=color, width=3)
        self.create_line(cx+r*0.55, cy-r*0.18, cx+r*0.55, cy+r*0.52, fill=color, width=3)

    def _icon_chart(self, cx, cy, r, color) -> None:
        widths = (0.26, 0.40, 0.54)
        heights = (0.55, 0.85, 1.15)
        starts = (-0.75, -0.22, 0.38)
        for start, w, h in zip(starts, widths, heights):
            x0 = cx + start*r
            self.create_rectangle(
                x0,
                cy+r*0.62-h*r,
                x0+w*r,
                cy+r*0.62,
                fill=color,
                outline="",
            )

    def _icon_road(self, cx, cy, r, color) -> None:
        self.create_polygon(
            cx-r*0.88, cy+r,
            cx-r*0.38, cy-r,
            cx+r*0.38, cy-r,
            cx+r*0.88, cy+r,
            fill=color,
            outline="",
        )
        self.create_polygon(
            cx-r*0.15, cy+r,
            cx-r*0.05, cy+r*0.42,
            cx+r*0.05, cy+r*0.42,
            cx+r*0.15, cy+r,
            fill=self._background,
            outline="",
        )
        self.create_line(cx, cy+r*0.18, cx, cy-r*0.25, fill=self._background, width=3)
        self.create_line(cx, cy-r*0.48, cx, cy-r*0.72, fill=self._background, width=2)
