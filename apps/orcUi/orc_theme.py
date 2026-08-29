# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared ORC UI theme palette and MapLibre style adaptation."""

from __future__ import annotations

import json
import tkinter as tk
from enum import Enum
from pathlib import Path
from typing import Any


class ThemeMode(str, Enum):
    DARK = "dark"
    LIGHT = "light"


DARK = {
    "bg": "#05090d",
    "panel": "#0b1117",
    "top": "#020406",
    "nav": "#070c11",
    "active": "#101820",
    "border": "#25313b",
    "text": "#edf2f5",
    "muted": "#89959e",
}

LIGHT = {
    "bg": "#eef2f5",
    "panel": "#ffffff",
    "top": "#dde4e9",
    "nav": "#e4e9ed",
    "active": "#d5dde3",
    "border": "#bcc7cf",
    "text": "#18232c",
    "muted": "#60707b",
}

ACCENT_BLUE = "#168bd1"
ACCENT_GREEN = "#84ce1f"
ACCENT_RED = "#f15a16"
ACCENT_PURPLE = "#a25ce5"
ACCENT_YELLOW = "#d6ad22"


_DARK_TO_LIGHT = {
    "#05090d": "#eef2f5",
    "#0b1117": "#ffffff",
    "#020406": "#dde4e9",
    "#070c11": "#e4e9ed",
    "#101820": "#d5dde3",
    "#121b23": "#d0d9df",
    "#25313b": "#bcc7cf",
    "#edf2f5": "#18232c",
    "#89959e": "#60707b",
    "#c7cdd2": "#3c4a54",
    "#b8c0c6": "#485760",
    "#aab2b8": "#56656f",
    "#c5ccd2": "#4f5d67",
    "#d7dde2": "#596872",
    "#53616c": "#6d7b85",
}
_LIGHT_TO_DARK = {value: key for key, value in _DARK_TO_LIGHT.items()}

_MAP_DARK_COLORS = {
    "#f3f1eb": "#0a0e12",
    "#d5e7cf": "#16231a",
    "#e7efd3": "#1b251b",
    "#e5ead4": "#1b231c",
    "#eee7ca": "#252317",
    "#ece8dd": "#171b1e",
    "#e9e5e0": "#171c20",
    "#ecdfd7": "#21191a",
    "#e1dcda": "#1c1b1e",
    "#dce7d6": "#172119",
    "#eadde4": "#211a20",
    "#ebe4cf": "#211f18",
    "#e7e3dc": "#191d20",
    "#d3e8ca": "#17301d",
    "#a8d4eb": "#102a38",
    "#88c5e6": "#24516a",
    "#aaa49d": "#56616a",
    "#9f9b96": "#59636a",
    "#c9c2b7": "#424b50",
    "#cbc6bf": "#384148",
    "#f7f5f1": "#59646c",
    "#c7c2bc": "#39434a",
    "#ffffff": "#68747c",
    "#b9b3ac": "#3c474f",
    "#faf8f3": "#626e76",
    "#c4a675": "#5a4d33",
    "#f2d59f": "#887548",
    "#b47f58": "#603f2d",
    "#efb674": "#a46d3c",
    "#c6c6c6": "#59636a",
    "#d8d4cf": "#242b30",
    "#cbc6c0": "#2d353a",
    "#b8b2ac": "#3b454c",
    "#eef8fc": "#0d171d",
    "#fff8e8": "#16130e",
    "#373431": "#d0d6da",
    "#353330": "#d6dcdf",
    "#f7f4ee": "#101418",
    "#626262": "#bcc5ca",
    "#675f56": "#bac2c6",
    "#f5f2eb": "#11161a",
    "#565149": "#c5cdd1",
    "#66554c": "#c9cfd2",
    "#7d766f": "#aeb8bd",
}


def palette(mode: ThemeMode) -> dict[str, str]:
    return DARK if mode is ThemeMode.DARK else LIGHT


def toggle(mode: ThemeMode) -> ThemeMode:
    return ThemeMode.LIGHT if mode is ThemeMode.DARK else ThemeMode.DARK


def toggle_label(mode: ThemeMode) -> str:
    return "☀  LIGHT" if mode is ThemeMode.DARK else "☾  DARK"


def apply_tk_theme(root: tk.Misc, mode: ThemeMode) -> None:
    """Recolor existing Tk widgets using the shared ORC semantic palette."""

    mapping = _DARK_TO_LIGHT if mode is ThemeMode.LIGHT else _LIGHT_TO_DARK
    _apply_widget(root, mapping)


def install_map_style(mode: ThemeMode, data_root: str | Path | None = None) -> Path | None:
    """Materialize the selected map theme into the normal deployed style path."""

    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "tools" / "map_builder" / "templates" / "openroadcode-style.json"
    root = Path(data_root or Path.home() / ".local" / "share" / "openroadcode")
    destination = root / "maps" / "styles" / "openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir():
        return None

    document = json.loads(template.read_text(encoding="utf-8"))
    if mode is ThemeMode.DARK:
        document = _replace_json_colors(document, _MAP_DARK_COLORS)
    destination.write_text(json.dumps(document, separators=(",", ":")), encoding="utf-8")
    return destination


def _apply_widget(widget: tk.Misc, mapping: dict[str, str]) -> None:
    for option in (
        "background",
        "foreground",
        "activebackground",
        "activeforeground",
        "highlightbackground",
        "highlightcolor",
        "insertbackground",
        "selectbackground",
        "selectforeground",
    ):
        try:
            current = str(widget.cget(option)).lower()
        except (tk.TclError, AttributeError):
            continue
        replacement = mapping.get(current)
        if replacement is not None:
            try:
                widget.configure(**{option: replacement})
            except tk.TclError:
                pass

    for child in widget.winfo_children():
        _apply_widget(child, mapping)


def _replace_json_colors(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        return mapping.get(value.lower(), value)
    if isinstance(value, list):
        return [_replace_json_colors(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: _replace_json_colors(item, mapping) for key, item in value.items()}
    return value
