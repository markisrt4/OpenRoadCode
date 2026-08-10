from __future__ import annotations

import tkinter as tk


_GLYPH_ICONS: dict[str, tuple[str, str]] = {
    "radio": ("◉", "#38a8ff"),
    "aircraft": ("✈", "#70c7ff"),
    "adsb": ("✈", "#70c7ff"),
    "airband_am": ("AM", "#70c7ff"),
    "gauges": ("◔", "#ffb020"),
    "gauges_placeholder": ("◔", "#ffb020"),
    "weather": ("☀", "#ffd24a"),
    "weather_dashboard": ("☀", "#ffd24a"),
    "noaa_weather_radio": ("☁", "#70c7ff"),
    "lighting": ("✦", "#f2d45c"),
    "media": ("▶", "#c58cff"),
    "fm_radio": ("FM", "#38a8ff"),
    "scanner_radio": ("⌁", "#48d11f"),
}


def create_menu_icon(
    parent: tk.Widget,
    *,
    key: str,
    size: int,
    background: str,
) -> tk.Canvas | None:
    """Create a compact icon for a known navigation tile."""
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=background,
        highlightthickness=0,
        borderwidth=0,
    )

    if key == "spotify":
        _draw_spotify(canvas, size)
    elif key == "netflix":
        _draw_netflix(canvas, size)
    elif key == "youtube":
        _draw_youtube(canvas, size)
    elif key in _GLYPH_ICONS:
        glyph, color = _GLYPH_ICONS[key]
        _draw_glyph(canvas, size, glyph, color)
    else:
        return None

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
