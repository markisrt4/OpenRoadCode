# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Mute an unavailable card, including its canvas artwork, reversibly."""
from __future__ import annotations

import tkinter as tk


def muted_color(widget: tk.Misc, color: str) -> str:
    red, green, blue = widget.winfo_rgb(color)
    # Pull both bright and dark colors toward neutral gray to reduce contrast.
    luminance = (red * 0.299 + green * 0.587 + blue * 0.114) / 257
    gray = round(luminance * 0.55 + 128 * 0.45)
    return f"#{gray:02x}{gray:02x}{gray:02x}"


class OfflineCardAppearance:
    """Keep original colors so switching online restores the entire card."""

    def __init__(self, card: tk.Misc) -> None:
        self._styles: list[tuple[tk.Misc, dict]] = []
        self._artwork: list[tuple[tk.Canvas, int, dict]] = []
        self._capture(card)

    def _capture(self, widget: tk.Misc) -> None:
        keys = widget.keys()
        colors = {name: widget.cget(name) for name in (
            "background", "foreground", "activebackground", "activeforeground",
            "highlightbackground", "highlightcolor", "disabledforeground",
        ) if name in keys and widget.cget(name)}
        if "cursor" in keys:
            colors["cursor"] = widget.cget("cursor")
        self._styles.append((widget, colors))
        if isinstance(widget, tk.Canvas):
            for item in widget.find_all():
                options = widget.itemconfigure(item)
                colors = {name: widget.itemcget(item, name) for name in ("fill", "outline")
                          if name in options and widget.itemcget(item, name)}
                self._artwork.append((widget, item, colors))
        for child in widget.winfo_children():
            self._capture(child)

    def set_online(self, online: bool) -> None:
        for widget, original in self._styles:
            values = original if online else {
                name: "arrow" if name == "cursor" else muted_color(widget, color)
                for name, color in original.items()
            }
            widget.configure(**values)
        for canvas, item, original in self._artwork:
            values = original if online else {
                name: muted_color(canvas, color) for name, color in original.items()
            }
            canvas.itemconfigure(item, **values)
