# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-friendly HSV color wheel for the Tk frontend."""

from __future__ import annotations

import math
import tkinter as tk

from common.color import HsvColor, RgbColor, hsv_to_rgb, rgb_to_hex, rgb_to_hsv
from ui.value import ColorValueRequestHandlerIf, ColorValueUiIf


class ColorWheel(tk.Canvas, ColorValueUiIf):
    """Render a hue/saturation wheel using generic color UI contracts."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        diameter: int = 220,
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
        self._sample_step = max(2, sample_step)
        self._marker: int | None = None
        self._handler: ColorValueRequestHandlerIf | None = None

        self._render_wheel()
        self.bind("<Button-1>", self._select)
        self.bind("<B1-Motion>", self._select)

    def set_color_request_handler(
        self,
        handler: ColorValueRequestHandlerIf | None,
    ) -> None:
        """Set the semantic consumer for user color selections."""
        self._handler = handler

    def set_color(self, color: RgbColor) -> None:
        """Move the selection marker to an RGB color without emitting it."""
        hsv = rgb_to_hsv(color)
        angle = math.radians(hsv.hue_degrees)
        distance = hsv.saturation * self._radius
        x = self._radius + math.cos(angle) * distance
        y = self._radius + math.sin(angle) * distance
        self._draw_marker(x, y, color)

    def _render_wheel(self) -> None:
        step = self._sample_step
        center = self._radius
        radius = self._radius

        for y in range(0, self._diameter, step):
            for x in range(0, self._diameter, step):
                dx = (x + step / 2) - center
                dy = (y + step / 2) - center
                saturation = math.hypot(dx, dy) / radius
                if saturation > 1.0:
                    continue

                hue_degrees = math.degrees(math.atan2(dy, dx)) % 360.0
                color = hsv_to_rgb(
                    HsvColor(
                        hue_degrees=hue_degrees,
                        saturation=saturation,
                        value=1.0,
                    )
                )
                color_hex = rgb_to_hex(color)
                self.create_rectangle(
                    x,
                    y,
                    min(x + step, self._diameter),
                    min(y + step, self._diameter),
                    fill=color_hex,
                    outline=color_hex,
                )

    def _select(self, event: tk.Event) -> None:
        dx = event.x - self._radius
        dy = event.y - self._radius
        distance = math.hypot(dx, dy)
        if distance > self._radius:
            return

        color = hsv_to_rgb(
            HsvColor(
                hue_degrees=math.degrees(math.atan2(dy, dx)) % 360.0,
                saturation=min(1.0, distance / self._radius),
                value=1.0,
            )
        )
        self._draw_marker(event.x, event.y, color)

        if self._handler is not None:
            self._handler.request_color(color)

    def _draw_marker(self, x: float, y: float, color: RgbColor) -> None:
        if self._marker is not None:
            self.delete(self._marker)

        radius = 7
        self._marker = self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            outline=(
                "#000000"
                if color.red + color.green + color.blue > 380
                else "#ffffff"
            ),
            width=3,
        )
