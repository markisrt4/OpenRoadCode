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
    "bg": "#e8e7e2",
    "panel": "#f7f6f2",
    "top": "#deddd8",
    "nav": "#e2e1dc",
    "active": "#d2d4d0",
    "border": "#b7b9b5",
    "text": "#202528",
    "muted": "#666e72",
}

ACCENT_BLUE = "#168bd1"
ACCENT_GREEN = "#84ce1f"
ACCENT_RED = "#f15a16"
ACCENT_PURPLE = "#a25ce5"
ACCENT_YELLOW = "#d6ad22"

_LIGHT_BLUE = "#0878b6"
_LIGHT_GREEN = "#5f9418"
_LIGHT_RED = "#c94d1a"
_LIGHT_PURPLE = "#7f49ad"
_LIGHT_YELLOW = "#927518"

_DARK_TO_LIGHT = {
    "#05090d": LIGHT["bg"],
    "#0b1117": LIGHT["panel"],
    "#020406": LIGHT["top"],
    "#070c11": LIGHT["nav"],
    "#101820": LIGHT["active"],
    "#121b23": "#ccceca",
    "#25313b": LIGHT["border"],
    "#edf2f5": LIGHT["text"],
    "#89959e": LIGHT["muted"],
    "#c7cdd2": "#444b4f",
    "#b8c0c6": "#52595d",
    "#aab2b8": "#60676b",
    "#c5ccd2": "#51585c",
    "#d7dde2": "#596064",
    "#53616c": "#737a7d",
    ACCENT_BLUE: _LIGHT_BLUE,
    ACCENT_GREEN: _LIGHT_GREEN,
    ACCENT_RED: _LIGHT_RED,
    ACCENT_PURPLE: _LIGHT_PURPLE,
    ACCENT_YELLOW: _LIGHT_YELLOW,
}
_LIGHT_TO_DARK = {value: key for key, value in _DARK_TO_LIGHT.items()}

# Keep the palette definitions available while dark-style transformation is
# isolated from renderer lifecycle debugging. The raw template is currently
# deployed unchanged so styling cannot invalidate or alter map layers.
_MAP_DARK = {
    "background": "#070b0f",
    "land": "#10161a",
    "wood": "#102319",
    "grass": "#15251a",
    "scrub": "#18241b",
    "farmland": "#222319",
    "residential": "#171d21",
    "commercial": "#201922",
    "industrial": "#1b2024",
    "cemetery": "#16241b",
    "hospital": "#241a20",
    "school": "#242119",
    "park": "#17331f",
    "water": "#082b3c",
    "waterway": "#22a9dc",
    "boundary": "#687279",
    "rail": "#626b71",
    "path": "#697178",
    "minor_casing": "#4b5359",
    "minor_road": "#c2c8cc",
    "secondary_casing": "#596168",
    "secondary_road": "#d5dade",
    "primary_casing": "#687178",
    "primary_road": "#e7eaec",
    "motorway_casing": "#747e85",
    "motorway": "#ffffff",
    "building": "#2c3337",
    "building_outline": "#51595f",
    "label": "#e1e5e7",
    "label_major": "#ffffff",
    "label_minor": "#c0c7cb",
    "label_halo": "#070b0f",
    "water_label": "#59c9ee",
    "poi_important": ACCENT_GREEN,
    "poi_food": ACCENT_PURPLE,
    "route_ref": ACCENT_RED,
    "place_label": "#f4f6f7",
}


def palette(mode: ThemeMode) -> dict[str, str]:
    return DARK if mode is ThemeMode.DARK else LIGHT


def toggle(mode: ThemeMode) -> ThemeMode:
    return ThemeMode.LIGHT if mode is ThemeMode.DARK else ThemeMode.DARK


def toggle_label(mode: ThemeMode) -> str:
    return "☀  LIGHT" if mode is ThemeMode.DARK else "☾  DARK"


def apply_tk_theme(root: tk.Misc, mode: ThemeMode) -> None:
    mapping = _DARK_TO_LIGHT if mode is ThemeMode.LIGHT else _LIGHT_TO_DARK
    _apply_widget(root, mapping)


def install_map_style(mode: ThemeMode, data_root: str | Path | None = None) -> Path | None:
    """Install the canonical style without modifying its MapLibre layer definitions."""

    del mode
    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "tools" / "map_builder" / "templates" / "openroadcode-style.json"
    root = Path(data_root or Path.home() / ".local" / "share" / "openroadcode")
    destination = root / "maps" / "styles" / "openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir():
        return None

    document = json.loads(template.read_text(encoding="utf-8"))
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


def _apply_dark_map_palette(document: dict[str, Any]) -> None:
    layers = {layer.get("id"): layer for layer in document.get("layers", [])}
    _paint(layers, "background", "background-color", _MAP_DARK["background"])


def _paint(
    layers: dict[str | None, dict[str, Any]],
    layer_id: str,
    property_name: str,
    value: Any,
) -> None:
    layer = layers.get(layer_id)
    if layer is not None:
        layer.setdefault("paint", {})[property_name] = value
