"""Shared Spotify and YouTube artwork for Tk media controls."""

import tkinter as tk

SPOTIFY_GREEN = "#1DB954"
YOUTUBE_RED = "#FF0033"


def draw_provider_logo(
    canvas: tk.Canvas, provider: str, size: int, *, muted: str | None = None
) -> None:
    """Draw the provider mark in a square at the requested size."""
    if provider == "spotify":
        color = muted or SPOTIFY_GREEN
        canvas.create_oval(5, 5, 53, 53, fill=color, outline=color)
        for bounds, width in (
            ((9, 12, 49, 35), 4),
            ((12, 20, 46, 40), 3),
            ((15, 28, 43, 45), 3),
        ):
            canvas.create_arc(
                *bounds,
                start=24,
                extent=135,
                style=tk.ARC,
                outline="#000000",
                width=max(1, round(width * size / 58)),
            )
    elif provider == "youtube":
        color = muted or YOUTUBE_RED
        mark = "#000000" if muted else "#FFFFFF"
        canvas.create_rectangle(8, 16, 50, 42, fill=color, outline=color)
        canvas.create_polygon(24, 21, 24, 37, 37, 29, fill=mark, outline=mark)
    else:
        raise ValueError(f"Unsupported provider logo: {provider}")
    canvas.scale("all", 0, 0, size / 58, size / 58)
