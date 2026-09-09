# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk rendering for toolkit-independent semantic icons."""

from __future__ import annotations

import tkinter as tk

from ui.icon import IconId


_GLYPH_ICONS: dict[IconId, tuple[str, str]] = {
    IconId.RADIO: ("◉", "#38a8ff"),
    IconId.AIRCRAFT: ("✈", "#70c7ff"),
    IconId.AIRBAND_AM: ("AM", "#70c7ff"),
    IconId.GAUGES: ("◔", "#ffb020"),
    IconId.WEATHER: ("☀", "#ffd24a"),
    IconId.WEATHER_RADIO: ("☁", "#70c7ff"),
    IconId.LIGHTING: ("✦", "#f2d45c"),
    IconId.MEDIA: ("▶", "#c58cff"),
    IconId.FM_RADIO: ("FM", "#38a8ff"),
    IconId.SCANNER_RADIO: ("⌁", "#48d11f"),
    IconId.POWER: ("⏻", "#edf2f5"),
    IconId.MICROPHONE: ("MIC", "#edf2f5"),
    IconId.CAMERA: ("CAM", "#edf2f5"),
    IconId.DISPLAY: ("▣", "#edf2f5"),
    IconId.BRIGHTNESS: ("☀", "#ffd24a"),
    IconId.VOLUME: ("VOL", "#edf2f5"),
    IconId.VOLUME_MUTED: ("MUTE", "#edf2f5"),
}


def create_icon(
    parent: tk.Widget,
    *,
    icon_id: IconId,
    size: int,
    background: str,
) -> tk.Canvas:
    """Render one semantic icon using Tk primitives."""
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=background,
        highlightthickness=0,
        borderwidth=0,
    )

    if icon_id is IconId.SPOTIFY:
        _draw_spotify(canvas, size)
    elif icon_id is IconId.NETFLIX:
        _draw_netflix(canvas, size)
    elif icon_id is IconId.YOUTUBE:
        _draw_youtube(canvas, size)
    else:
        glyph, color = _GLYPH_ICONS.get(icon_id, ("?", "#edf2f5"))
        _draw_glyph(canvas, size, glyph, color)
    return canvas


def _draw_spotify(canvas: tk.Canvas, size: int) -> None:
    padding = max(1, size // 16)
    canvas.create_oval(
        padding,
        padding,
        size - padding,
        size - padding,
        fill="#1ED760",
        outline="",
    )
    line_width = max(2, size // 13)
    wave_points = (
        (0.20, 0.34, 0.38, 0.27, 0.59, 0.29, 0.80, 0.38),
        (0.23, 0.50, 0.40, 0.44, 0.58, 0.46, 0.76, 0.53),
        (0.27, 0.65, 0.42, 0.61, 0.57, 0.62, 0.72, 0.68),
    )
    for points in wave_points:
        canvas.create_line(
            *(coordinate * size for coordinate in points),
            fill="#101010",
            width=line_width,
            smooth=True,
            splinesteps=20,
            capstyle="round",
        )


def _draw_netflix(canvas: tk.Canvas, size: int) -> None:
    canvas.create_text(
        size / 2,
        size / 2,
        text="N",
        fill="#E50914",
        font=("DejaVu Sans", max(18, int(size * 0.8)), "bold"),
    )


def _draw_youtube(canvas: tk.Canvas, size: int) -> None:
    padding = max(1, size // 12)
    canvas.create_rectangle(
        padding,
        size * 0.20,
        size - padding,
        size * 0.80,
        fill="#FF0000",
        outline="",
    )
    canvas.create_polygon(
        size * 0.42,
        size * 0.34,
        size * 0.42,
        size * 0.66,
        size * 0.68,
        size * 0.50,
        fill="#FFFFFF",
        outline="",
    )


def _draw_glyph(
    canvas: tk.Canvas,
    size: int,
    glyph: str,
    color: str,
) -> None:
    font_size = int(size * (0.46 if len(glyph) > 1 else 0.72))
    canvas.create_text(
        size / 2,
        size / 2,
        text=glyph,
        fill=color,
        font=("DejaVu Sans", max(12, font_size), "bold"),
    )
