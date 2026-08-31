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
    "bg": "#05090d", "panel": "#0b1117", "top": "#020406", "nav": "#070c11",
    "active": "#101820", "border": "#25313b", "text": "#edf2f5", "muted": "#89959e",
}
LIGHT = {
    "bg": "#e8edf0", "panel": "#f6f8f9", "top": "#dce3e7", "nav": "#e1e7ea",
    "active": "#d1dbe0", "border": "#b3c0c7", "text": "#20282d", "muted": "#66747c",
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
    "#05090d": LIGHT["bg"], "#0b1117": LIGHT["panel"], "#020406": LIGHT["top"],
    "#070c11": LIGHT["nav"], "#101820": LIGHT["active"], "#121b23": "#c8d2d7",
    "#25313b": LIGHT["border"], "#edf2f5": LIGHT["text"], "#89959e": LIGHT["muted"],
    "#c7cdd2": "#46535a", "#b8c0c6": "#536169", "#aab2b8": "#606e75",
    "#c5ccd2": "#515f66", "#d7dde2": "#59676e", "#53616c": "#737f85",
    ACCENT_BLUE: _LIGHT_BLUE, ACCENT_GREEN: _LIGHT_GREEN, ACCENT_RED: _LIGHT_RED,
    ACCENT_PURPLE: _LIGHT_PURPLE, ACCENT_YELLOW: _LIGHT_YELLOW,
}
_LIGHT_TO_DARK = {value: key for key, value in _DARK_TO_LIGHT.items()}

# Dark mode intentionally uses visibly separated hues. On a small automotive
# display, tiny luminance differences collapse into one muddy surface.
_MAP_DARK = {
    "background": "#0b151b",
    "wood": "#164a35", "grass": "#28523a", "scrub": "#314b3b", "farmland": "#51482b",
    "land_default": "#17262d", "residential": "#22343d", "commercial": "#493044",
    "industrial": "#33444a", "cemetery": "#24513b", "hospital": "#542f42",
    "school": "#564d29", "landuse_default": "#293940", "park": "#17613b",
    "water": "#075078", "waterway": "#21b8ed", "boundary": "#73858e",
    "rail": "#718087", "path": "#7b898f", "service_casing": "#39484f",
    "service": "#718087", "residential_casing": "#46565d", "residential_road": "#8d9ba1",
    "secondary_casing": "#275e78", "secondary_road": "#73b7d8",
    "primary_casing": "#075d8d", "primary_road": "#31ace9",
    "motorway_casing": "#034c79", "motorway": "#00a9ff", "aeroway": "#75848b",
    "building": "#3b494f", "building_outline": "#596970",
    "route_casing": "#ffffff", "route": "#ff4935",
    "label": "#e1e9ec", "label_major": "#ffffff", "label_minor": "#c5d0d5",
    "label_halo": "#081116", "water_label": "#76ddff", "road_ref": "#b1e3f5",
    "poi": "#bfff55", "poi_food": "#ff7448", "house": "#a8b6bc",
}

_MAP_LIGHT = {
    "background": "#e7eef2", "wood": "#a9d4b8", "grass": "#c8e3b2", "scrub": "#d1e1c3",
    "farmland": "#eadb9e", "land_default": "#e1e8e8", "residential": "#e1e7eb",
    "commercial": "#eddbe7", "industrial": "#d9e2e5", "cemetery": "#c5dfcb",
    "hospital": "#efd7e2", "school": "#f0e4b9", "landuse_default": "#dee6e7",
    "park": "#a9dcb7", "water": "#75bee3", "waterway": "#2da6df", "boundary": "#82949e",
    "rail": "#8b989e", "path": "#a1acae", "service_casing": "#b9c3c7", "service": "#f2f5f6",
    "residential_casing": "#b1bdc3", "residential_road": "#ffffff",
    "secondary_casing": "#70a5bc", "secondary_road": "#c1e2f1",
    "primary_casing": "#277fae", "primary_road": "#62b8e2", "motorway_casing": "#146e9f",
    "motorway": "#269bd4", "aeroway": "#a1adb2", "building": "#c6d1d6",
    "building_outline": "#9eacb3", "route_casing": "#ffffff", "route": "#e33b24",
    "label": "#2e3d45", "label_major": "#17252c", "label_minor": "#52636c",
    "label_halo": "#f5f8f9", "water_label": "#146f9f", "road_ref": "#205f80",
    "poi": "#477f12", "poi_food": "#c54226", "house": "#697980",
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
    """Install the canonical style with explicit ORC light/dark paint overrides."""
    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "tools" / "map_builder" / "templates" / "openroadcode-style.json"
    root = Path(data_root or Path.home() / ".local" / "share" / "openroadcode")
    destination = root / "maps" / "styles" / "openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir():
        return None
    document = json.loads(template.read_text(encoding="utf-8"))
    _apply_map_palette(document, _MAP_DARK if mode is ThemeMode.DARK else _MAP_LIGHT)
    destination.write_text(json.dumps(document, separators=(",", ":")), encoding="utf-8")
    return destination


def _apply_widget(widget: tk.Misc, mapping: dict[str, str]) -> None:
    for option in ("background", "foreground", "activebackground", "activeforeground",
                   "highlightbackground", "highlightcolor", "insertbackground",
                   "selectbackground", "selectforeground"):
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


def _apply_map_palette(document: dict[str, Any], colors: dict[str, str]) -> None:
    layers = {layer.get("id"): layer for layer in document.get("layers", [])}
    _paint(layers, "background", "background-color", colors["background"])
    _paint(layers, "landcover", "fill-color", ["match", ["get", "class"],
        "wood", colors["wood"], "grass", colors["grass"], "scrub", colors["scrub"],
        "farmland", colors["farmland"], colors["land_default"]])
    _paint(layers, "landuse", "fill-color", ["match", ["get", "class"],
        "residential", colors["residential"], "commercial", colors["commercial"],
        "industrial", colors["industrial"], "cemetery", colors["cemetery"],
        "hospital", colors["hospital"], "school", colors["school"], colors["landuse_default"]])
    _paint(layers, "parks", "fill-color", colors["park"])
    _paint(layers, "water", "fill-color", colors["water"])
    _paint(layers, "waterways", "line-color", colors["waterway"])
    _paint(layers, "boundaries", "line-color", colors["boundary"])
    _paint(layers, "railways", "line-color", colors["rail"])
    _paint(layers, "paths", "line-color", colors["path"])
    for layer_id, color_key in (
        ("service-roads-casing", "service_casing"), ("service-roads", "service"),
        ("residential-roads-casing", "residential_casing"), ("residential-roads", "residential_road"),
        ("secondary-roads-casing", "secondary_casing"), ("secondary-roads", "secondary_road"),
        ("primary-roads-casing", "primary_casing"), ("primary-roads", "primary_road"),
        ("motorways-casing", "motorway_casing"), ("motorways", "motorway"), ("aeroways", "aeroway")):
        _paint(layers, layer_id, "line-color", colors[color_key])
    _paint(layers, "buildings", "fill-color", colors["building"])
    _paint(layers, "buildings", "fill-outline-color", colors["building_outline"])
    _paint(layers, "route-line-casing", "line-color", colors["route_casing"])
    _paint(layers, "route-line", "line-color", colors["route"])
    _paint_label(layers, "water-labels", colors["water_label"], colors["label_halo"])
    _paint_label(layers, "road-refs-major", colors["road_ref"], colors["label_halo"])
    _paint_label(layers, "road-labels", colors["label"], colors["label_halo"])
    _paint_label(layers, "place-labels", colors["label_major"], colors["label_halo"])
    _paint_label(layers, "aerodrome-labels", colors["label_minor"], colors["label_halo"])
    _paint_label(layers, "mountain-peaks", colors["label_minor"], colors["label_halo"])
    _paint_label(layers, "poi-labels-important", colors["poi"], colors["label_halo"])
    _paint_label(layers, "poi-labels-food", colors["poi_food"], colors["label_halo"])
    _paint_label(layers, "house-numbers", colors["house"], colors["label_halo"])


def _paint_label(layers: dict[str | None, dict[str, Any]], layer_id: str,
                 text_color: str, halo_color: str) -> None:
    _paint(layers, layer_id, "text-color", text_color)
    _paint(layers, layer_id, "text-halo-color", halo_color)


def _paint(layers: dict[str | None, dict[str, Any]], layer_id: str,
           property_name: str, value: Any) -> None:
    layer = layers.get(layer_id)
    if layer is not None:
        layer.setdefault("paint", {})[property_name] = value
