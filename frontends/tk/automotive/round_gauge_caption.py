# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Round automotive instrument with its name outside the dial."""

from __future__ import annotations

import tkinter as tk

from frontends.tk.automotive.vehicle_gauge_widgets import RoundGauge as BaseRoundGauge


class RoundGauge(BaseRoundGauge):
    """Reserve a caption strip below the circular instrument."""

    def _draw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        # Keep the instrument circular even when the host is resized.
        # The caption is outside the bezel, not over the needle or scale.
        caption_height = max(18, min(30, int(min(width, height) * 0.13)))
        dial_height = max(1, height - caption_height)
        size = min(width, dial_height)
        cx, cy = width / 2, dial_height / 2
        radius = size * 0.46

        rings = (
            (1.00, self._style.bezel_outer),
            (0.975, self._style.bezel_shadow),
            (0.935, self._style.bezel_metal_dark),
            (0.905, self._style.bezel_metal_light),
            (0.875, self._style.bezel_midlight),
            (0.845, self._style.bezel_inner),
            (0.815, self._style.face_shadow),
            (0.792, self._style.face_color),
        )
        for scale, color in rings:
            r = radius * scale
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=color)

        r = radius * 0.755
        self.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=25, extent=130, style=tk.ARC,
            outline=self._style.face_highlight,
            width=max(2, int(size * 0.008)),
        )
        self._draw_operating_bands(cx, cy, radius)
        self._draw_ticks(cx, cy, radius)
        self._draw_labels(cx, cy, radius)
        self._draw_needle(cx, cy, radius)
        self._draw_center(cx, cy, radius)
        self.create_text(
            cx, dial_height + caption_height / 2,
            text=self._title.upper(),
            fill=self._style.foreground_color,
            font=(self._style.condensed_font_family, max(9, int(radius * 0.12)), "bold"),
            width=max(1, width - 8),
        )

    def _draw_labels(self, cx: float, cy: float, radius: float) -> None:
        # Preserve the unit, value display and connection state while removing
        # only the title from the face. The title is drawn in the caption strip.
        self.create_text(
            cx, cy - radius * 0.16,
            text=self._unit.upper(),
            fill=self._style.muted_color,
            font=(self._style.font_family, max(6, int(radius * 0.075)), "bold"),
        )
        value_text = "--" if self._value is None else f"{self._value:.{self._precision}f}"
        if not self._connected:
            value_text = "OFF"
        self.create_text(
            cx, cy + radius * 0.13,
            text="PERFORMANCE",
            fill=self._style.performance_label,
            font=(self._style.condensed_font_family, max(5, int(radius * 0.055)), "bold"),
        )
        box_w, box_h = radius * 0.58, radius * 0.18
        box_y = cy + radius * 0.61
        self.create_rectangle(
            cx - box_w / 2, box_y - box_h / 2,
            cx + box_w / 2, box_y + box_h / 2,
            fill=self._style.display_color,
            outline=self._style.display_border,
            width=max(2, int(radius * 0.016)),
        )
        self.create_text(
            cx, box_y, text=value_text,
            fill=self._style.display_text if self._connected else self._style.muted_color,
            font=(self._style.mono_font_family, max(8, int(radius * 0.12)), "bold"),
        )
