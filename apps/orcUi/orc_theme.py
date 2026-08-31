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


DARK = {"bg":"#05090d","panel":"#0b1117","top":"#020406","nav":"#070c11","active":"#101820","border":"#25313b","text":"#edf2f5","muted":"#89959e"}
LIGHT = {"bg":"#e8e7e2","panel":"#f7f6f2","top":"#deddd8","nav":"#e2e1dc","active":"#d2d4d0","border":"#b7b9b5","text":"#202528","muted":"#666e72"}

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

_DARK_TO_LIGHT = {"#05090d":LIGHT["bg"],"#0b1117":LIGHT["panel"],"#020406":LIGHT["top"],"#070c11":LIGHT["nav"],"#101820":LIGHT["active"],"#121b23":"#ccceca","#25313b":LIGHT["border"],"#edf2f5":LIGHT["text"],"#89959e":LIGHT["muted"],"#c7cdd2":"#444b4f","#b8c0c6":"#52595d","#aab2b8":"#60676b","#c5ccd2":"#51585c","#d7dde2":"#596064","#53616c":"#737a7d",ACCENT_BLUE:_LIGHT_BLUE,ACCENT_GREEN:_LIGHT_GREEN,ACCENT_RED:_LIGHT_RED,ACCENT_PURPLE:_LIGHT_PURPLE,ACCENT_YELLOW:_LIGHT_YELLOW}
_LIGHT_TO_DARK = {value:key for key,value in _DARK_TO_LIGHT.items()}

# Deliberately higher-contrast than a conventional dark basemap. This is an
# automotive display: roads and destinations need to read at a glance, not win
# an award for tasteful charcoal-on-slightly-different-charcoal restraint.
_MAP_DARK = {
    "background":"#0a1015","land":"#172128","wood":"#163624","grass":"#1b4028","scrub":"#233b28","farmland":"#3a3820",
    "residential":"#202b32","commercial":"#35262e","industrial":"#2b3038","cemetery":"#203728","hospital":"#3b252d","school":"#3c3523","park":"#1c4d2b",
    "water":"#073d59","waterway":"#27b9ed","boundary":"#87949d","rail":"#7e8990","path":"#929ba1",
    "minor_casing":"#46545d","minor_road":"#b7c1c7","secondary_casing":"#335f79","secondary_road":"#8fc7e7","primary_casing":"#075d91","primary_road":"#32a9ed","motorway_casing":"#07466c","motorway":"#168bd1",
    "building":"#37434a","building_outline":"#66747c","label":"#f0f4f6","label_major":"#ffffff","label_minor":"#d2dadd","label_halo":"#071015","water_label":"#62d5f6",
    "poi_important":ACCENT_GREEN,"poi_food":ACCENT_PURPLE,"route_ref":ACCENT_RED,"place_label":"#ffffff",
}


def palette(mode: ThemeMode) -> dict[str,str]:
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
    root = Path(data_root or Path.home()/".local"/"share"/"openroadcode")
    destination = root/"maps"/"styles"/"openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir():
        return None
    document = json.loads(template.read_text(encoding="utf-8"))
    if mode is ThemeMode.DARK:
        _apply_dark_map_palette(document)
    destination.write_text(json.dumps(document,separators=(",",":")),encoding="utf-8")
    return destination


def _apply_widget(widget: tk.Misc, mapping: dict[str,str]) -> None:
    for option in ("background","foreground","activebackground","activeforeground","highlightbackground","highlightcolor","insertbackground","selectbackground","selectforeground"):
        try: current = str(widget.cget(option)).lower()
        except (tk.TclError,AttributeError): continue
        replacement = mapping.get(current)
        if replacement is not None:
            try: widget.configure(**{option:replacement})
            except tk.TclError: pass
    for child in widget.winfo_children(): _apply_widget(child,mapping)


def _apply_dark_map_palette(document: dict[str,Any]) -> None:
    layers = {layer.get("id"):layer for layer in document.get("layers",[])}
    _paint(layers,"background","background-color",_MAP_DARK["background"])
    _paint(layers,"landcover","fill-color",["match",["get","class"],"wood",_MAP_DARK["wood"],"grass",_MAP_DARK["grass"],"scrub",_MAP_DARK["scrub"],"farmland",_MAP_DARK["farmland"],_MAP_DARK["land"]])
    _paint(layers,"landuse","fill-color",["match",["get","class"],"residential",_MAP_DARK["residential"],"commercial",_MAP_DARK["commercial"],"industrial",_MAP_DARK["industrial"],"cemetery",_MAP_DARK["cemetery"],"hospital",_MAP_DARK["hospital"],"school",_MAP_DARK["school"],_MAP_DARK["residential"]])
    for lid,key,prop in (("parks","park","fill-color"),("water","water","fill-color"),("waterways","waterway","line-color"),("boundaries","boundary","line-color"),("railways","rail","line-color"),("paths","path","line-color")):_paint(layers,lid,prop,_MAP_DARK[key])
    _paint(layers,"waterways","line-opacity",1.0)
    for lid in ("service-roads-casing","residential-roads-casing"):_paint(layers,lid,"line-color",_MAP_DARK["minor_casing"])
    for lid in ("service-roads","residential-roads"):_paint(layers,lid,"line-color",_MAP_DARK["minor_road"])
    for prefix,key in (("secondary","secondary"),("primary","primary"),("motorways","motorway")):
        casing_id = f"{prefix}-roads-casing" if prefix != "motorways" else "motorways-casing"
        road_id = f"{prefix}-roads" if prefix != "motorways" else "motorways"
        _paint(layers,casing_id,"line-color",_MAP_DARK[f"{key}_casing"])
        _paint(layers,road_id,"line-color",_MAP_DARK[key])
    _paint(layers,"aeroways","line-color",_MAP_DARK["secondary_road"])
    building=layers.get("buildings")
    if building is not None:
        paint=building.setdefault("paint",{});paint["fill-color"]=_MAP_DARK["building"];paint["fill-outline-color"]=_MAP_DARK["building_outline"]
    _symbol(layers,"water-labels",_MAP_DARK["water_label"]);_symbol(layers,"road-refs-major",_MAP_DARK["route_ref"],halo_width=2.0);_symbol(layers,"road-labels",_MAP_DARK["label"],halo_width=1.8);_symbol(layers,"place-labels",_MAP_DARK["place_label"],halo_width=2.2);_symbol(layers,"aerodrome-labels",_MAP_DARK["label_minor"]);_symbol(layers,"mountain-peaks",_MAP_DARK["label_minor"]);_symbol(layers,"poi-labels-important",_MAP_DARK["poi_important"],halo_width=1.9);_symbol(layers,"poi-labels-food",_MAP_DARK["poi_food"],halo_width=1.8);_symbol(layers,"house-numbers",_MAP_DARK["label_minor"],halo_width=1.2)


def _paint(layers: dict[str|None,dict[str,Any]],layer_id:str,property_name:str,value:Any)->None:
    layer=layers.get(layer_id)
    if layer is not None: layer.setdefault("paint",{})[property_name]=value


def _symbol(layers:dict[str|None,dict[str,Any]],layer_id:str,text_color:str,*,halo_width:float=1.6)->None:
    layer=layers.get(layer_id)
    if layer is None:return
    paint=layer.setdefault("paint",{});paint["text-color"]=text_color;paint["text-halo-color"]=_MAP_DARK["label_halo"];paint["text-halo-width"]=halo_width
