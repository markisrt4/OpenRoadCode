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

# Light mode is intentionally warm-neutral rather than blue-white.  The ORC
# accent colors already provide plenty of color, so the chrome should stay
# quiet and let information win the visual hierarchy battle.
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

# The map palettes are semantic rather than an inversion of the daytime style.
# Night mode deliberately suppresses local detail while keeping important roads,
# labels, the route, and vehicle marker legible at a glance.
_MAP_DARK = {
    "background": "#090b0d",
    "land": "#0d1012",
    "residential": "#101417",
    "commercial": "#151316",
    "industrial": "#141518",
    "park": "#101912",
    "water": "#091820",
    "waterway": "#173546",
    "boundary": "#343c42",
    "rail": "#343b40",
    "path": "#252b2f",
    "minor_casing": "#181d20",
    "minor_road": "#252b30",
    "secondary_casing": "#23292d",
    "secondary_road": "#343c42",
    "primary_casing": "#30383e",
    "primary_road": "#48535b",
    "motorway_casing": "#3c464d",
    "motorway": "#59656d",
    "building": "#171c1f",
    "building_outline": "#252c30",
    "label": "#929ba1",
    "label_major": "#aeb6bb",
    "label_minor": "#778087",
    "label_halo": "#090b0d",
    "water_label": "#5f879b",
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
        _apply_dark_map_palette(document)
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

    _paint(layers, "landcover", "fill-color", _MAP_DARK["land"])
    _paint(layers, "landuse", "fill-color", _MAP_DARK["residential"])
    _paint(layers, "parks", "fill-color", _MAP_DARK["park"])
    _paint(layers, "water", "fill-color", _MAP_DARK["water"])
    _paint(layers, "waterways", "line-color", _MAP_DARK["waterway"])
    _paint(layers, "boundaries", "line-color", _MAP_DARK["boundary"])
    _paint(layers, "railways", "line-color", _MAP_DARK["rail"])
    _paint(layers, "paths", "line-color", _MAP_DARK["path"])

    for layer_id in ("service-roads-casing", "residential-roads-casing"):
        _paint(layers, layer_id, "line-color", _MAP_DARK["minor_casing"])
    for layer_id in ("service-roads", "residential-roads"):
        _paint(layers, layer_id, "line-color", _MAP_DARK["minor_road"])

    _paint(layers, "secondary-roads-casing", "line-color", _MAP_DARK["secondary_casing"])
    _paint(layers, "secondary-roads", "line-color", _MAP_DARK["secondary_road"])
    _paint(layers, "primary-roads-casing", "line-color", _MAP_DARK["primary_casing"])
    _paint(layers, "primary-roads", "line-color", _MAP_DARK["primary_road"])
    _paint(layers, "motorways-casing", "line-color", _MAP_DARK["motorway_casing"])
    _paint(layers, "motorways", "line-color", _MAP_DARK["motorway"])
    _paint(layers, "aeroways", "line-color", _MAP_DARK["secondary_road"])

    building = layers.get("buildings")
    if building is not None:
        paint = building.setdefault("paint", {})
        paint["fill-color"] = _MAP_DARK["building"]
        paint["fill-outline-color"] = _MAP_DARK["building_outline"]

    _symbol(layers, "water-labels", _MAP_DARK["water_label"])
    _symbol(layers, "road-refs-major", _MAP_DARK["label_major"])
    _symbol(layers, "road-labels", _MAP_DARK["label"])
    _symbol(layers, "place-labels", _MAP_DARK["label_major"])
    _symbol(layers, "aerodrome-labels", _MAP_DARK["label_minor"])
    _symbol(layers, "mountain-peaks", _MAP_DARK["label_minor"])
    _symbol(layers, "poi-labels-important", _MAP_DARK["label"])
    _symbol(layers, "poi-labels-food", _MAP_DARK["label_minor"])
    _symbol(layers, "house-numbers", _MAP_DARK["label_minor"])


def _paint(
    layers: dict[str | None, dict[str, Any]],
    layer_id: str,
    property_name: str,
    value: str,
) -> None:
    layer = layers.get(layer_id)
    if layer is not None:
        layer.setdefault("paint", {})[property_name] = value


def _symbol(
    layers: dict[str | None, dict[str, Any]],
    layer_id: str,
    text_color: str,
) -> None:
    layer = layers.get(layer_id)
    if layer is None:
        return
    paint = layer.setdefault("paint", {})
    paint["text-color"] = text_color
    paint["text-halo-color"] = _MAP_DARK["label_halo"]
    paint["text-halo-width"] = 1.25
