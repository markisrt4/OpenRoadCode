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

# High-contrast automotive night palette. The canvas stays dark, but the road
# network is intentionally much brighter than surrounding map detail so it can
# be read with a quick glance rather than studied like a cartography exam.
_MAP_DARK = {
    "background": "#07090b",
    "land": "#0c1013",
    "residential": "#10161a",
    "commercial": "#171419",
    "industrial": "#15171a",
    "park": "#102016",
    "water": "#081a24",
    "waterway": "#39738f",
    "boundary": "#59636a",
    "rail": "#535c62",
    "path": "#596167",
    "minor_casing": "#252b2f",
    "minor_road": "#7b858c",
    "secondary_casing": "#333a3f",
    "secondary_road": "#9aa4aa",
    "primary_casing": "#41494f",
    "primary_road": "#c2c9cd",
    "motorway_casing": "#525b61",
    "motorway": "#eef1f2",
    "building": "#252b2f",
    "building_outline": "#444c51",
    "label": "#d7dcdf",
    "label_major": "#f4f6f7",
    "label_minor": "#b5bdc2",
    "label_halo": "#07090b",
    "water_label": "#91bfd4",
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
    paint["text-halo-width"] = 1.5
