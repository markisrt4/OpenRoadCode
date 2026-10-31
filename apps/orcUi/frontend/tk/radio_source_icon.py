# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radio source icon drawing for the orcUi radio chooser."""

from __future__ import annotations

import tkinter as tk
import math

from ui.theme import ThemeBundle


def draw_source_scene(canvas: tk.Canvas, *, icon_kind: str, accent: str,
                      theme: ThemeBundle, width: int, height: int) -> None:
    """Illustrate RF reception or internet stations without live telemetry."""
    canvas.delete("all")
    if width < 2 or height < 2:
        return
    ui = theme.ui
    base = canvas.winfo_rgb(ui.surface)
    tint = canvas.winfo_rgb(accent)
    for index in range(32):
        amount = 0.22 * (1 - index / 31)
        color = "#" + "".join(f"{round((a + (b - a) * amount) / 257):02x}"
                              for a, b in zip(base, tint))
        canvas.create_rectangle(width * index / 32, 0,
                                width * (index + 1) / 32 + 1, height,
                                fill=color, outline="")
    sx, sy = width / 360, height / 96

    def line(points, **kwargs):
        canvas.create_line(*(value * (sx if index % 2 == 0 else sy)
                             for index, value in enumerate(points)), **kwargs)

    if icon_kind == "rf":
        line((35, 69, 48, 28, 61, 69, 35, 69), fill=ui.text, width=2)
        line((41, 51, 55, 51, 38, 61, 58, 61), fill=ui.text_muted, width=1)
        for radius in (13, 23, 33):
            canvas.create_arc((48 - radius) * sx, (28 - radius) * sy,
                              (48 + radius) * sx, (28 + radius) * sy,
                              start=25, extent=130, style=tk.ARC,
                              outline=accent, width=2)
        points = []
        for index in range(100):
            x = 102 + index * 2.35
            envelope = math.exp(-((index - 48) / 26) ** 2)
            y = 45 + math.sin(index * 0.6) * 23 * envelope
            points.extend((x, y))
        line(points, fill=accent, width=2, smooth=True)
        caption = "AIRWAVES  ›  SDR  ›  AUDIO"
    elif icon_kind == "trending":
        heights = (21, 34, 27, 51, 44, 68, 58, 78, 65, 86)
        for index, top in enumerate(heights):
            x = (28 + index * 29) * sx
            canvas.create_rectangle(x, top * sy, x + 15 * sx, 75 * sy,
                                    fill=accent if index >= 6 else ui.text_muted, outline="")
        line((25, 61, 57, 49, 87, 56, 117, 33, 147, 40, 177, 20, 207, 29, 237, 12, 267, 19, 300, 7),
             fill=ui.text, width=3, smooth=True)
        caption = "AIRPLAY  ›  CHARTS  ›  DISCOVER"
    else:
        canvas.create_oval(22 * sx, 12 * sy, 74 * sx, 64 * sy,
                           outline=accent, width=2)
        canvas.create_oval(36 * sx, 12 * sy, 60 * sx, 64 * sy,
                           outline=ui.text_muted, width=1)
        line((22, 38, 74, 38), fill=ui.text_muted, width=1)
        for x, y in ((150, 24), (216, 48), (300, 22), (319, 60)):
            line((78, 38, x, y), fill=ui.border, width=2)
            canvas.create_oval((x - 6) * sx, (y - 6) * sy,
                               (x + 6) * sx, (y + 6) * sy,
                               fill=accent, outline="")
        caption = "INTERNET  ›  STATION  ›  AUDIO"
    canvas.create_text(12 * sx, 83 * sy, text=caption, anchor="w",
                       fill=ui.text_muted, font=("Sans", 9, "bold"))


def draw_source_icon(
    canvas: tk.Canvas,
    *,
    icon_kind: str,
    accent: str,
    theme: ThemeBundle,
) -> None:
    """Draw the RF or streaming source icon."""
    ui = theme.ui
    canvas.create_oval(5, 5, 59, 59, outline=accent, width=2)
    if icon_kind == "rf":
        canvas.create_line(32, 47, 32, 28, fill=ui.text, width=3)
        canvas.create_oval(28, 24, 36, 32, fill=accent, outline=accent)
        canvas.create_arc(19, 15, 45, 41, start=310, extent=100, style=tk.ARC, outline=accent, width=2)
        canvas.create_arc(12, 8, 52, 48, start=310, extent=100, style=tk.ARC, outline=ui.text_muted, width=2)
        canvas.create_line(23, 51, 41, 51, fill=ui.text_muted, width=2)
        return

    if icon_kind == "trending":
        for index, height in enumerate((12, 22, 16, 30)):
            x = 15 + index * 10
            canvas.create_rectangle(x, 48 - height, x + 6, 48,
                                    fill=accent if index == 3 else ui.text_muted, outline="")
        canvas.create_line(15, 37, 25, 28, 35, 33, 46, 17,
                           fill=ui.text, width=2, smooth=True)
        return
    canvas.create_oval(27, 27, 37, 37, fill=accent, outline=accent)
    canvas.create_arc(20, 20, 44, 44, start=315, extent=90, style=tk.ARC, outline=accent, width=2)
    canvas.create_arc(13, 13, 51, 51, start=315, extent=90, style=tk.ARC, outline=ui.text_muted, width=2)
    canvas.create_arc(7, 7, 57, 57, start=315, extent=90, style=tk.ARC, outline=accent, width=2)
