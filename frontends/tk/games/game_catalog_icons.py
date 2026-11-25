# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Find and scale local game artwork."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path

_ICON_SIZES = (128, 96, 64, 48, 32, 256)


def _find_game_icon(icon_name: str) -> Path | None:
    prefix = Path(os.environ.get("PREFIX", "/usr"))
    for root in (prefix / "share" / "pixmaps", Path("/usr/share/pixmaps")):
        for extension in ("png", "gif"):
            candidate = root / f"{icon_name}.{extension}"
            if candidate.is_file():
                return candidate
    for root in (prefix / "share" / "icons", Path("/usr/share/icons")):
        for icon_theme in ("hicolor", "breeze", "breeze-dark", "Adwaita"):
            for size in _ICON_SIZES:
                for context in ("apps", "applications"):
                    for extension in ("png", "gif"):
                        candidate = (
                            root
                            / icon_theme
                            / f"{size}x{size}"
                            / context
                            / f"{icon_name}.{extension}"
                        )
                        if candidate.is_file():
                            return candidate
    return None


def _load_game_icon(path: Path | None) -> tk.PhotoImage | None:
    image: tk.PhotoImage | None = None
    if path is not None:
        try:
            image = tk.PhotoImage(file=str(path))
            maximum = max(image.width(), image.height())
            if maximum > 56:
                image = image.subsample(max(1, (maximum + 55) // 56), max(1, (maximum + 55) // 56))
        except tk.TclError:
            image = None
    return image


def game_icon(
    icon_name: str | None, cache: dict[str, tk.PhotoImage | None]
) -> tk.PhotoImage | None:
    if not icon_name:
        return None
    if icon_name not in cache:
        cache[icon_name] = _load_game_icon(_find_game_icon(icon_name))
    return cache[icon_name]
