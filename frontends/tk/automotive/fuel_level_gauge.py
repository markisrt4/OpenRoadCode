# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Segmented round fuel-level gauge for automotive Tk frontends."""

from __future__ import annotations

import math
import tkinter as tk

from apps.common.uiTheme import VEHICLE_GAUGE_THEME, VehicleGaugeTheme


class FuelLevelGauge(tk.Canvas):
    """Compact round fuel gauge with discrete level tiers."""

    SEGMENT_COUNT = 12
    START_ANGLE_DEG = 145.0
    SWEEP_ANGLE_DEG = 250.0

    def __init__(
        self,
        master: tk.Misc,
        *,
        style: VehicleGaugeTheme | None = None,
        size: int = 122,
        **kwargs: object,
    ) -> None:
        self._style = style or VEHICLE_GAUGE_THEME
        self._value: float | None = None
        self._connected = True
        super().__init__(
            master,
            width=size,
            height=size,
            background=self._style.background_color,
            highlightthickness=0,
            **kwargs,
        )
        self.bind("<Configure>", self._on_resize)
        self.after_idle(self._draw)

    @property
    def value(self) -> float | None:
        """Return the displayed fuel percentage."""
        return self._value

    def set_value(self, value: float | int | None) -> None:
        """Set fuel level as a percentage in the inclusive range 0..100."""
        self._value = None if value is None else max(0.0, min(100.0, float(value)))
        self._draw()

    def set_connected(self, connected: bool) -> None:
        """Set whether live vehicle telemetry is available."""
        self._connected = connected
        self._draw()

    @classmethod
    def active_segment_count(cls, fuel_percent: float | None) -> int:
        """Return how many discrete segments should illuminate."""
        if fuel_percent is None:
            return 0
        clamped = max(0.0, min(100.0, float(fuel_percent)))
        if clamped <= 0.0:
            return 0
        return min(cls.SEGMENT_COUNT, math.ceil(clamped / 100.0 * cls.SEGMENT_COUNT))

    @staticmethod
    def level_tier(fuel_percent: float | None) -> str:
        """Classify fuel level for normal, caution, or danger treatment."""
        if fuel_percent is None:
            return "unknown"
        if fuel_percent <= 12.5:
            return "danger"
        if fuel_percent <= 25.0:
            return "caution"
        return "normal"

    def _on_resize(self, _event: tk.Event[tk.Misc]) -> None:
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        size = min(width, height)
        cx, cy = width / 2.0, height / 2.0
        radius = size * 0.46

        for scale, color in (
            (1.00, self._style.bezel_outer),
            (0.96, self._style.bezel_shadow),
            (0.91, self._style.bezel_metal_dark),
            (0.87, self._style.bezel_midlight),
            (0.82, self._style.bezel_inner),
            (0.77, self._style.face_color),
        ):
            r = radius * scale
            self.create_oval(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                fill=color,
                outline=color,
            )

        # Give the gauge a permanent visual scale so an unavailable fuel signal
        # still looks like an instrument instead of an empty black circle.
        arc_r = radius * 0.66
        self.create_arc(
            cx - arc_r,
            cy - arc_r,
            cx + arc_r,
            cy + arc_r,
            start=-(self.START_ANGLE_DEG + self.SWEEP_ANGLE_DEG),
            extent=self.SWEEP_ANGLE_DEG,
            style=tk.ARC,
            outline=self._style.muted_detail,
            width=max(1, int(size * 0.012)),
        )

        active_count = self.active_segment_count(self._value) if self._connected else 0
        for index in range(self.SEGMENT_COUNT):
            ratio = index / max(1, self.SEGMENT_COUNT - 1)
            angle_deg = self.START_ANGLE_DEG + ratio * self.SWEEP_ANGLE_DEG
            angle = math.radians(angle_deg)
            segment_percent = ratio * 100.0
            active = index < active_count
            color = self._segment_color(segment_percent, active)
            inner = radius * 0.55
            outer = radius * 0.73
            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle)
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle)
            self.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                width=max(4, int(size * 0.045)),
                capstyle=tk.ROUND,
            )

        self.create_text(
            cx,
            cy - radius * 0.31,
            text="FUEL",
            fill=self._style.primary_text,
            font=(
                self._style.condensed_font_family,
                max(8, int(radius * 0.13)),
                "bold",
            ),
        )

        if not self._connected:
            value_text = "OFF"
            detail_text = "NO DATA"
        elif self._value is None:
            value_text = "--"
            detail_text = "NO DATA"
        else:
            value_text = f"{self._value:.0f}"
            detail_text = "%"

        self.create_text(
            cx,
            cy + radius * 0.01,
            text=value_text,
            fill=self._value_color(),
            font=(
                self._style.mono_font_family,
                max(15, int(radius * 0.33)),
                "bold",
            ),
        )
        self.create_text(
            cx,
            cy + radius * 0.31,
            text=detail_text,
            fill=self._style.muted_detail,
            font=(
                self._style.condensed_font_family,
                max(7, int(radius * 0.10)),
                "bold",
            ),
        )
        self.create_text(
            cx - radius * 0.54,
            cy + radius * 0.55,
            text="E",
            fill=self._style.danger_value,
            font=(self._style.font_family, max(8, int(radius * 0.11)), "bold"),
        )
        self.create_text(
            cx + radius * 0.54,
            cy + radius * 0.55,
            text="F",
            fill=self._style.primary_text,
            font=(self._style.font_family, max(8, int(radius * 0.11)), "bold"),
        )

    def _segment_color(self, segment_percent: float, active: bool) -> str:
        if not active:
            # ``disabled_normal_value`` is intentionally very subdued for normal
            # gauges and was nearly invisible here. Fuel needs a visible scale.
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
        return self._style.primary_text
