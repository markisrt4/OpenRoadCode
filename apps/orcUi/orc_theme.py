# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""MapLibre style adaptation and small theme-mode presentation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui.theme import ThemeMode

_MAP_DARK = {
    "background": "#0b151b", "wood": "#164a35", "grass": "#28523a", "scrub": "#314b3b", "farmland": "#3b5140",
    "land_default": "#17262d", "residential": "#22343d", "commercial": "#40334d", "industrial": "#33444a", "cemetery": "#24513b", "hospital": "#4b3349", "school": "#354b52", "landuse_default": "#293940", "park": "#17613b",
    "water": "#075078", "waterway": "#21b8ed", "boundary": "#73858e", "rail": "#718087", "path": "#7b898f", "service_casing": "#39484f", "service": "#718087", "residential_casing": "#46565d", "residential_road": "#8d9ba1", "secondary_casing": "#275e78", "secondary_road": "#73b7d8", "primary_casing": "#075d8d", "primary_road": "#31ace9", "motorway_casing": "#034c79", "motorway": "#00a9ff", "aeroway": "#75848b", "building": "#3b494f", "building_outline": "#596970", "route_casing": "#ffffff", "route": "#ff4935", "label": "#e1e9ec", "label_major": "#ffffff", "label_minor": "#c5d0d5", "label_halo": "#081116", "water_label": "#76ddff", "road_ref": "#b1e3f5", "poi": "#bfff55", "poi_food": "#ff7448", "house": "#a8b6bc",
}
_MAP_LIGHT = {
    "background": "#e7eef2", "wood": "#a9d4b8", "grass": "#c8e3b2", "scrub": "#d1e1c3", "farmland": "#dce6b4", "land_default": "#e1e8e8", "residential": "#e1e7eb", "commercial": "#eddbe7", "industrial": "#d9e2e5", "cemetery": "#c5dfcb", "hospital": "#efd7e2", "school": "#dce8df", "landuse_default": "#dee6e7", "park": "#a9dcb7", "water": "#75bee3", "waterway": "#2da6df", "boundary": "#82949e", "rail": "#8b989e", "path": "#a1acae", "service_casing": "#b9c3c7", "service": "#f2f5f6", "residential_casing": "#b1bdc3", "residential_road": "#ffffff", "secondary_casing": "#70a5bc", "secondary_road": "#c1e2f1", "primary_casing": "#277fae", "primary_road": "#62b8e2", "motorway_casing": "#146e9f", "motorway": "#269bd4", "aeroway": "#a1adb2", "building": "#c6d1d6", "building_outline": "#9eacb3", "route_casing": "#ffffff", "route": "#e33b24", "label": "#2e3d45", "label_major": "#17252c", "label_minor": "#52636c", "label_halo": "#f5f8f9", "water_label": "#146f9f", "road_ref": "#205f80", "poi": "#477f12", "poi_food": "#c54226", "house": "#697980",
}


def toggle(mode: ThemeMode) -> ThemeMode:
    return ThemeMode.LIGHT if mode is ThemeMode.DARK else ThemeMode.DARK


def toggle_label(mode: ThemeMode) -> str:
    return "☀  LIGHT" if mode is ThemeMode.DARK else "☾  DARK"


def install_map_style(mode: ThemeMode, data_root: str | Path | None = None) -> Path | None:
    """Install the generated MapLibre style for the requested presentation mode."""
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


def _apply_map_palette(document: dict[str, Any], colors: dict[str, str]) -> None:
    layers = {layer.get("id"): layer for layer in document.get("layers", [])}
    _paint(layers, "background", "background-color", colors["background"])
    _paint(layers, "landcover", "fill-color", ["match", ["get", "class"], "wood", colors["wood"], "grass", colors["grass"], "scrub", colors["scrub"], "farmland", colors["farmland"], colors["land_default"]])
    _paint(layers, "landuse", "fill-color", ["match", ["get", "class"], "residential", colors["residential"], "commercial", colors["commercial"], "industrial", colors["industrial"], "cemetery", colors["cemetery"], "hospital", colors["hospital"], "school", colors["school"], colors["landuse_default"]])
    for layer_id, property_name, key in (
        ("parks", "fill-color", "park"), ("water", "fill-color", "water"), ("waterways", "line-color", "waterway"), ("boundaries", "line-color", "boundary"), ("railways", "line-color", "rail"), ("paths", "line-color", "path"), ("service-roads-casing", "line-color", "service_casing"), ("service-roads", "line-color", "service"), ("residential-roads-casing", "line-color", "residential_casing"), ("residential-roads", "line-color", "residential_road"), ("secondary-roads-casing", "line-color", "secondary_casing"), ("secondary-roads", "line-color", "secondary_road"), ("primary-roads-casing", "line-color", "primary_casing"), ("primary-roads", "line-color", "primary_road"), ("motorways-casing", "line-color", "motorway_casing"), ("motorways", "line-color", "motorway"), ("aeroways", "line-color", "aeroway"), ("buildings", "fill-color", "building"), ("buildings", "fill-outline-color", "building_outline"), ("route-line-casing", "line-color", "route_casing"), ("route-line", "line-color", "route"),
    ):
        _paint(layers, layer_id, property_name, colors[key])
    _paint(layers, "primary-roads-casing", "line-width", 5.5)
    _paint(layers, "primary-roads", "line-width", 4.5)
    _paint(layers, "motorways-casing", "line-width", 6.5)
    _paint(layers, "motorways", "line-width", 5)
    for layer_id, key in (("water-labels", "water_label"), ("road-refs-major", "road_ref"), ("road-labels", "label"), ("place-labels", "label_major"), ("aerodrome-labels", "label_minor"), ("mountain-peaks", "label_minor"), ("poi-labels-important", "poi"), ("poi-labels-food", "poi_food"), ("house-numbers", "house")):
        _paint_label(layers, layer_id, colors[key], colors["label_halo"])


def _paint_label(layers: dict[str, dict[str, Any]], layer_id: str, text_color: str, halo_color: str) -> None:
    _paint(layers, layer_id, "text-color", text_color)
    _paint(layers, layer_id, "text-halo-color", halo_color)


def _paint(layers: dict[str, dict[str, Any]], layer_id: str, property_name: str, value: Any) -> None:
    layer = layers.get(layer_id)
    if layer is not None:
        layer.setdefault("paint", {})[property_name] = value
