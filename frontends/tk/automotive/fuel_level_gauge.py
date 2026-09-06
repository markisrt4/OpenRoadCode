# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Analog round fuel-level gauge for automotive Tk frontends."""

from __future__ import annotations

import math
import tkinter as tk

from apps.common.uiTheme import VEHICLE_GAUGE_THEME, VehicleGaugeTheme


class FuelLevelGauge(tk.Canvas):
    """Compact analog fuel gauge with a needle and graduated level scale."""

    SEGMENT_COUNT = 12
    START_ANGLE_DEG = 145.0
    SWEEP_ANGLE_DEG = 250.0

    def __init__(
        self,
        master: tk.Misc,
        *,
        style: VehicleGaugeTheme | None = None,
        size: int = 122,
        show_title: bool = True,
        **kwargs: object,
    ) -> None:
        self._style = style or VEHICLE_GAUGE_THEME
        self._value: float | None = None
        self._connected = True
        self._show_title = show_title
        super().__init__(master, width=size, height=size, background=self._style.background_color, highlightthickness=0, **kwargs)
        self.bind("<Configure>", self._on_resize)
        self.after_idle(self._draw)

    @property
    def value(self) -> float | None:
        return self._value

    def set_value(self, value: float | int | None) -> None:
        self._value = None if value is None else max(0.0, min(100.0, float(value)))
        self._draw()

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._draw()

    @classmethod
    def active_segment_count(cls, fuel_percent: float | None) -> int:
        if fuel_percent is None:
            return 0
        clamped = max(0.0, min(100.0, float(fuel_percent)))
        if clamped <= 0.0:
            return 0
        return min(cls.SEGMENT_COUNT, math.ceil(clamped / 100.0 * cls.SEGMENT_COUNT))

    @staticmethod
    def level_tier(fuel_percent: float | None) -> str:
        if fuel_percent is None:
            return "unknown"
        if fuel_percent <= 12.5:
            return "danger"
        if fuel_percent <= 25.0:
            return "caution"
        return "normal"

    def _on_resize(self, _event: tk.Event[tk.Misc]) -> None:
        self._draw()

    @staticmethod
    def _point(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
        angle = math.radians(angle_deg)
        return cx + radius * math.cos(angle), cy + radius * math.sin(angle)

    def _draw(self) -> None:
        self.delete("all")
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        size = min(width, height)
        cx, cy = width / 2.0, height / 2.0
        radius = size * 0.46

        for scale, color in ((1.00, self._style.bezel_outer), (0.96, self._style.bezel_shadow), (0.91, self._style.bezel_metal_dark), (0.87, self._style.bezel_midlight), (0.82, self._style.bezel_inner), (0.77, self._style.face_color)):
            r = radius * scale
            self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline=color)

        # Twenty minor divisions, with quarter-tank marks emphasized.
        for index in range(21):
            ratio = index / 20.0
            angle = self.START_ANGLE_DEG + ratio * self.SWEEP_ANGLE_DEG
            major = index % 5 == 0
            inner = radius * (0.52 if major else 0.61)
            outer = radius * 0.72
            x1, y1 = self._point(cx, cy, inner, angle)
            x2, y2 = self._point(cx, cy, outer, angle)
            percent = ratio * 100.0
            color = self._style.danger_value if percent <= 12.5 else self._style.caution_value if percent <= 25.0 else self._style.foreground_color if major else self._style.muted_detail
            self.create_line(x1, y1, x2, y2, fill=color, width=max(2, int(size * (0.024 if major else 0.012))), capstyle=tk.ROUND)

        # Keep labels sparse at this size. Fractions inside a 122 px dial turned
        # into visual confetti; E, 1/2 and F give the useful reference points.
        for percent, label in ((0, "E"), (50, "1/2"), (100, "F")):
            angle = self.START_ANGLE_DEG + (percent / 100.0) * self.SWEEP_ANGLE_DEG
            tx, ty = self._point(cx, cy, radius * 0.42, angle)
            color = self._style.danger_value if percent == 0 else self._style.foreground_color
            self.create_text(tx, ty, text=label, fill=color, font=(self._style.condensed_font_family, max(7, int(radius * 0.105)), "bold"))

        if self._show_title:
            self.create_text(cx, cy - radius * 0.24, text="FUEL", fill=self._style.foreground_color, font=(self._style.condensed_font_family, max(8, int(radius * 0.13)), "bold"))

        needle_value = 0.0 if self._value is None or not self._connected else self._value
        needle_angle = self.START_ANGLE_DEG + (needle_value / 100.0) * self.SWEEP_ANGLE_DEG
        needle_color = self._style.accent_color if self._value is not None and self._connected else self._style.muted_color
        nx, ny = self._point(cx, cy, radius * 0.55, needle_angle)
        tail_x, tail_y = self._point(cx, cy, -radius * 0.10, needle_angle)
        self.create_line(tail_x, tail_y, nx, ny, fill=needle_color, width=max(3, int(size * 0.026)), capstyle=tk.ROUND)
        hub = max(3.0, size * 0.035)
        self.create_oval(cx-hub, cy-hub, cx+hub, cy+hub, fill=self._style.hub_metal, outline=self._style.hub_outer, width=max(1, int(size * 0.008)))

        detail = "--" if not self._connected or self._value is None else f"{self._value:.0f}%"
        detail_color = self._style.muted_color if self._value is None or not self._connected else self._value_color()
        self.create_text(cx, cy + radius * 0.38, text=detail, fill=detail_color, font=(self._style.mono_font_family, max(7, int(radius * 0.11)), "bold"))

    def _segment_color(self, segment_percent: float, active: bool) -> str:
        if not active:
            return self._style.muted_detail
        if segment_percent <= 12.5:
            return self._style.danger_value
        if segment_percent <= 25.0:
            return self._style.caution_value
        return self._style.normal_value

    def _value_color(self) -> str:
        if not self._connected or self._value is None:
            return self._style.muted_color
        tier = self.level_tier(self._value)
        if tier == "danger":
            return self._style.danger_value
        if tier == "caution":
            return self._style.caution_value
        return self._style.foreground_color
