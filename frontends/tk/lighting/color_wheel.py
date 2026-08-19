# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-friendly HSV color wheel for the Tk lighting frontend."""

from __future__ import annotations

import colorsys
import math
import tkinter as tk
from collections.abc import Callable

from ui.lighting import LightingColor


class ColorWheel(tk.Canvas):
    """Render an HSV hue/saturation wheel and emit selected RGB colors."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        diameter: int = 260,
        on_color: Callable[[LightingColor], None] | None = None,
        background: str = "#111111",
        sample_step: int = 4,
    ) -> None:
        super().__init__(
            parent,
            width=diameter,
            height=diameter,
            bg=background,
            highlightthickness=0,
            bd=0,
        )
        self._diameter = diameter
        self._radius = diameter / 2
        self._on_color = on_color
        self._sample_step = max(2, sample_step)
        self._marker: int | None = None
        self._photo = tk.PhotoImage(width=diameter, height=diameter)
        self.create_image(0, 0, image=self._photo, anchor="nw")
        self._render_wheel()
        self.bind("<Button-1>", self._select)
        self.bind("<B1-Motion>", self._select)

    def set_color(self, color: LightingColor) -> None:
        """Move the selection marker to an RGB color without emitting it."""
        red, green, blue = (channel / 255 for channel in (color.red, color.green, color.blue))
        hue, saturation, _value = colorsys.rgb_to_hsv(red, green, blue)
        angle = hue * math.tau
        distance = saturation * self._radius
        x = self._radius + math.cos(angle) * distance
        y = self._radius + math.sin(angle) * distance
        self._draw_marker(x, y, color)

    def _render_wheel(self) -> None:
        step = self._sample_step
        center = self._radius
        radius = self._radius
        for y in range(0, self._diameter, step):
            row: list[str] = []
            for x in range(0, self._diameter, step):
                dx = (x + step / 2) - center
                dy = (y + step / 2) - center
                saturation = math.hypot(dx, dy) / radius
                if saturation > 1:
                    row.append(self.cget("bg"))
                    continue
                hue = (math.atan2(dy, dx) % math.tau) / math.tau
                red, green, blue = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                row.append(f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}")
            for yy in range(y, min(y + step, self._diameter)):
                self._photo.put("{" + " ".join(row) + "}", to=(0, yy, len(row), yy + 1))
        # Scale the sampled image horizontally when sample_step > 1 by drawing
        # rectangles over it; PhotoImage has no inexpensive arbitrary scaling.
        if step > 1:
            self.delete("all")
            for y in range(0, self._diameter, step):
                for x in range(0, self._diameter, step):
                    dx = (x + step / 2) - center
                    dy = (y + step / 2) - center
                    saturation = math.hypot(dx, dy) / radius
                    if saturation > 1:
                        continue
                    hue = (math.atan2(dy, dx) % math.tau) / math.tau
                    red, green, blue = colorsys.hsv_to_rgb(hue, saturation, 1.0)
                    color = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
                    self.create_rectangle(x, y, x + step, y + step, fill=color, outline=color)

    def _select(self, event: tk.Event) -> None:
        dx = event.x - self._radius
        dy = event.y - self._radius
        distance = math.hypot(dx, dy)
        if distance > self._radius:
            return
        saturation = min(1.0, distance / self._radius)
        hue = (math.atan2(dy, dx) % math.tau) / math.tau
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, 1.0)
        color = LightingColor(round(red * 255), round(green * 255), round(blue * 255))
        self._draw_marker(event.x, event.y, color)
        if self._on_color is not None:
            self._on_color(color)

    def _draw_marker(self, x: float, y: float, color: LightingColor) -> None:
        if self._marker is not None:
            self.delete(self._marker)
        radius = 7
        # Black/white double marker remains visible over any wheel color.
        self._marker = self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            outline="#000000" if sum((color.red, color.green, color.blue)) > 380 else "#ffffff",
            width=3,
        )
