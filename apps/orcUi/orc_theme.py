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
    "bg": "#e8edf0",
    "panel": "#f6f8f9",
    "top": "#dce3e7",
    "nav": "#e1e7ea",
    "active": "#d1dbe0",
    "border": "#b3c0c7",
    "text": "#20282d",
    "muted": "#66747c",
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
    "#121b23": "#c8d2d7",
    "#25313b": LIGHT["border"],
    "#edf2f5": LIGHT["text"],
    "#89959e": LIGHT["muted"],
    "#c7cdd2": "#46535a",
    "#b8c0c6": "#536169",
    "#aab2b8": "#606e75",
    "#c5ccd2": "#515f66",
    "#d7dde2": "#59676e",
    "#53616c": "#737f85",
    ACCENT_BLUE: _LIGHT_BLUE,
    ACCENT_GREEN: _LIGHT_GREEN,
    ACCENT_RED: _LIGHT_RED,
    ACCENT_PURPLE: _LIGHT_PURPLE,
    ACCENT_YELLOW: _LIGHT_YELLOW,
}
_LIGHT_TO_DARK = {value: key for key, value in _DARK_TO_LIGHT.items()}

_MAP_DARK = {
    "background": "#081015",
    "wood": "#102a20",
    "grass": "#173322",
    "scrub": "#193025",
    "farmland": "#252b20",
    "land_default": "#131b20",
    "residential": "#182229",
    "commercial": "#251f29",
    "industrial": "#20292d",
    "cemetery": "#183126",
    "hospital": "#2a2028",
    "school": "#2b2920",
    "landuse_default": "#1b2429",
    "park": "#17412a",
    "water": "#08354d",
    "waterway": "#1e9fd2",
    "boundary": "#667780",
    "rail": "#64717a",
    "path": "#718087",
    "service_casing": "#3f4c53",
    "service": "#a9b6bd",
    "residential_casing": "#485860",
    "residential_road": "#c4ced3",
    "secondary_casing": "#355c72",
    "secondary_road": "#8fc5df",
    "primary_casing": "#155c84",
    "primary_road": "#3aa2da",
    "motorway_casing": "#0b527c",
    "motorway": "#168bd1",
    "aeroway": "#6f7e85",
    "building": "#2a3439",
    "building_outline": "#4f5e65",
    "route_casing": "#f6f8f9",
    "route": ACCENT_RED,
    "label": "#d6e0e5",
    "label_major": "#f5f8fa",
    "label_minor": "#b5c2c8",
    "label_halo": "#081015",
    "water_label": "#65c8ee",
    "road_ref": "#9fd3ea",
    "poi": "#b9c5ca",
    "poi_food": "#d0b5dc",
    "house": "#9eabb1",
}

_MAP_LIGHT = {
    "background": "#e8eef1",
    "wood": "#c7dfcf",
    "grass": "#d8e7c9",
    "scrub": "#dce5d2",
    "farmland": "#e7e1c7",
    "land_default": "#e3e8e7",
    "residential": "#e3e8eb",
    "commercial": "#ebe2e8",
    "industrial": "#dde4e6",
    "cemetery": "#d5e5d9",
    "hospital": "#eadfe6",
    "school": "#eae7d7",
    "landuse_default": "#e1e6e7",
    "park": "#bfe0c6",
    "water": "#8fc9e5",
    "waterway": "#60b4df",
    "boundary": "#8c9ba3",
    "rail": "#929da3",
    "path": "#a3adaf",
    "service_casing": "#b8c1c5",
    "service": "#f4f7f8",
    "residential_casing": "#b2bec4",
    "residential_road": "#ffffff",
    "secondary_casing": "#8aaebe",
    "secondary_road": "#d8edf6",
    "primary_casing": "#4f98bd",
    "primary_road": "#8bc9e8",
    "motorway_casing": "#287fae",
    "motorway": "#57aee0",
    "aeroway": "#a8b2b7",
    "building": "#cbd4d8",
    "building_outline": "#a7b4ba",
    "route_casing": "#ffffff",
    "route": "#df331f",
    "label": "#334149",
    "label_major": "#202c32",
    "label_minor": "#56656d",
    "label_halo": "#f4f7f8",
    "water_label": "#246f98",
    "road_ref": "#2e6683",
    "poi": "#536169",
    "poi_food": "#765e76",
    "house": "#707d84",
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


def _apply_map_palette(document: dict[str, Any], colors: dict[str, str]) -> None:
    """Override only known canonical layer paint properties.

    Keeping this list explicit protects the renderer from accidental mutations of
    unrelated layer definitions while still allowing the UI theme to own colors.
    """

    layers = {layer.get("id"): layer for layer in document.get("layers", [])}

    _paint(layers, "background", "background-color", colors["background"])
    _paint(
        layers,
        "landcover",
        "fill-color",
        [
            "match",
            ["get", "class"],
            "wood", colors["wood"],
            "grass", colors["grass"],
            "scrub", colors["scrub"],
            "farmland", colors["farmland"],
            colors["land_default"],
        ],
    )
    _paint(
        layers,
        "landuse",
        "fill-color",
        [
            "match",
            ["get", "class"],
            "residential", colors["residential"],
            "commercial", colors["commercial"],
            "industrial", colors["industrial"],
            "cemetery", colors["cemetery"],
            "hospital", colors["hospital"],
            "school", colors["school"],
            colors["landuse_default"],
        ],
    )
    _paint(layers, "parks", "fill-color", colors["park"])
    _paint(layers, "water", "fill-color", colors["water"])
    _paint(layers, "waterways", "line-color", colors["waterway"])
    _paint(layers, "boundaries", "line-color", colors["boundary"])
    _paint(layers, "railways", "line-color", colors["rail"])
    _paint(layers, "paths", "line-color", colors["path"])

    for layer_id, color_key in (
        ("service-roads-casing", "service_casing"),
        ("service-roads", "service"),
        ("residential-roads-casing", "residential_casing"),
        ("residential-roads", "residential_road"),
        ("secondary-roads-casing", "secondary_casing"),
        ("secondary-roads", "secondary_road"),
        ("primary-roads-casing", "primary_casing"),
        ("primary-roads", "primary_road"),
        ("motorways-casing", "motorway_casing"),
        ("motorways", "motorway"),
        ("aeroways", "aeroway"),
    ):
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


def _paint_label(
    layers: dict[str | None, dict[str, Any]],
    layer_id: str,
    text_color: str,
    halo_color: str,
) -> None:
    _paint(layers, layer_id, "text-color", text_color)
    _paint(layers, layer_id, "text-halo-color", halo_color)


def _paint(
    layers: dict[str | None, dict[str, Any]],
    layer_id: str,
    property_name: str,
    value: Any,
) -> None:
    layer = layers.get(layer_id)
    if layer is not None:
        layer.setdefault("paint", {})[property_name] = value
