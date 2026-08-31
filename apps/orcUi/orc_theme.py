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
ACCENT_BLUE="#168bd1"; ACCENT_GREEN="#84ce1f"; ACCENT_RED="#f15a16"; ACCENT_PURPLE="#a25ce5"; ACCENT_YELLOW="#d6ad22"
_LIGHT_BLUE="#0878b6"; _LIGHT_GREEN="#5f9418"; _LIGHT_RED="#c94d1a"; _LIGHT_PURPLE="#7f49ad"; _LIGHT_YELLOW="#927518"
_DARK_TO_LIGHT={"#05090d":LIGHT["bg"],"#0b1117":LIGHT["panel"],"#020406":LIGHT["top"],"#070c11":LIGHT["nav"],"#101820":LIGHT["active"],"#121b23":"#ccceca","#25313b":LIGHT["border"],"#edf2f5":LIGHT["text"],"#89959e":LIGHT["muted"],"#c7cdd2":"#444b4f","#b8c0c6":"#52595d","#aab2b8":"#60676b","#c5ccd2":"#51585c","#d7dde2":"#596064","#53616c":"#737a7d",ACCENT_BLUE:_LIGHT_BLUE,ACCENT_GREEN:_LIGHT_GREEN,ACCENT_RED:_LIGHT_RED,ACCENT_PURPLE:_LIGHT_PURPLE,ACCENT_YELLOW:_LIGHT_YELLOW}
_LIGHT_TO_DARK={value:key for key,value in _DARK_TO_LIGHT.items()}

_MAP_DARK={
 "background":"#060b10","land":"#0d151b","wood":"#10291d","grass":"#173222","scrub":"#162a20","farmland":"#292719",
 "residential":"#121c24","commercial":"#251b27","industrial":"#1b232a","cemetery":"#173022","hospital":"#321c22","school":"#302919","park":"#164329",
 "water":"#06314a","waterway":"#159bd1","boundary":"#526575","rail":"#53616b","path":"#5e6d77",
 "minor_casing":"#263945","minor_road":"#9eafb9","secondary_casing":"#254c65","secondary_road":"#b8d1df","primary_casing":"#0d5d8c","primary_road":"#54a9d6","motorway_casing":"#075181","motorway":"#168bd1",
 "building":"#202c33","building_outline":"#40515b","label":"#d5e0e6","label_major":"#f3f8fa","label_minor":"#a8bac4","label_halo":"#050b10","water_label":"#55c6ec","poi_important":ACCENT_GREEN,"poi_food":ACCENT_PURPLE,"route_ref":ACCENT_RED,"place_label":"#edf4f7"}

def palette(mode:ThemeMode)->dict[str,str]: return DARK if mode is ThemeMode.DARK else LIGHT
def toggle(mode:ThemeMode)->ThemeMode: return ThemeMode.LIGHT if mode is ThemeMode.DARK else ThemeMode.DARK
def toggle_label(mode:ThemeMode)->str: return "☀  LIGHT" if mode is ThemeMode.DARK else "☾  DARK"

def apply_tk_theme(root:tk.Misc,mode:ThemeMode)->None:
    mapping=_DARK_TO_LIGHT if mode is ThemeMode.LIGHT else _LIGHT_TO_DARK
    _apply_widget(root,mapping)

def install_map_style(mode:ThemeMode,data_root:str|Path|None=None)->Path|None:
    repo_root=Path(__file__).resolve().parents[2]; template=repo_root/"tools"/"map_builder"/"templates"/"openroadcode-style.json"
    root=Path(data_root or Path.home()/".local"/"share"/"openroadcode"); destination=root/"maps"/"styles"/"openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir(): return None
    document=json.loads(template.read_text(encoding="utf-8"))
    if mode is ThemeMode.DARK: _apply_dark_map_palette(document)
    destination.write_text(json.dumps(document,separators=(",",":")),encoding="utf-8"); return destination

def _apply_widget(widget:tk.Misc,mapping:dict[str,str])->None:
    for option in ("background","foreground","activebackground","activeforeground","highlightbackground","highlightcolor","insertbackground","selectbackground","selectforeground"):
        try: current=str(widget.cget(option)).lower()
        except (tk.TclError,AttributeError): continue
        replacement=mapping.get(current)
        if replacement is not None:
            try: widget.configure(**{option:replacement})
            except tk.TclError: pass
    for child in widget.winfo_children(): _apply_widget(child,mapping)

def _apply_dark_map_palette(document:dict[str,Any])->None:
    layers={layer.get("id"):layer for layer in document.get("layers",[])}
    _paint(layers,"background","background-color",_MAP_DARK["background"])
    _paint(layers,"landcover","fill-color",["match",["get","class"],"wood",_MAP_DARK["wood"],"grass",_MAP_DARK["grass"],"scrub",_MAP_DARK["scrub"],"farmland",_MAP_DARK["farmland"],_MAP_DARK["land"]])
    _paint(layers,"landuse","fill-color",["match",["get","class"],"residential",_MAP_DARK["residential"],"commercial",_MAP_DARK["commercial"],"industrial",_MAP_DARK["industrial"],"cemetery",_MAP_DARK["cemetery"],"hospital",_MAP_DARK["hospital"],"school",_MAP_DARK["school"],_MAP_DARK["residential"]])
    _paint(layers,"parks","fill-color",_MAP_DARK["park"]); _paint(layers,"water","fill-color",_MAP_DARK["water"]); _paint(layers,"waterways","line-color",_MAP_DARK["waterway"]); _paint(layers,"waterways","line-opacity",1.0)
    _paint(layers,"boundaries","line-color",_MAP_DARK["boundary"]); _paint(layers,"railways","line-color",_MAP_DARK["rail"]); _paint(layers,"paths","line-color",_MAP_DARK["path"])
    for i in ("service-roads-casing","residential-roads-casing"): _paint(layers,i,"line-color",_MAP_DARK["minor_casing"])
    for i in ("service-roads","residential-roads"): _paint(layers,i,"line-color",_MAP_DARK["minor_road"])
    _paint(layers,"secondary-roads-casing","line-color",_MAP_DARK["secondary_casing"]); _paint(layers,"secondary-roads","line-color",_MAP_DARK["secondary_road"])
    _paint(layers,"primary-roads-casing","line-color",_MAP_DARK["primary_casing"]); _paint(layers,"primary-roads","line-color",_MAP_DARK["primary_road"])
    _paint(layers,"motorways-casing","line-color",_MAP_DARK["motorway_casing"]); _paint(layers,"motorways","line-color",_MAP_DARK["motorway"]); _paint(layers,"aeroways","line-color",_MAP_DARK["secondary_road"])
    building=layers.get("buildings")
    if building is not None:
        paint=building.setdefault("paint",{}); paint["fill-color"]=_MAP_DARK["building"]; paint["fill-outline-color"]=_MAP_DARK["building_outline"]
    _symbol(layers,"water-labels",_MAP_DARK["water_label"]); _symbol(layers,"road-refs-major",_MAP_DARK["route_ref"],halo_width=2.0); _symbol(layers,"road-labels",_MAP_DARK["label"],halo_width=1.8); _symbol(layers,"place-labels",_MAP_DARK["place_label"],halo_width=2.2)
    _symbol(layers,"aerodrome-labels",_MAP_DARK["label_minor"]); _symbol(layers,"mountain-peaks",_MAP_DARK["label_minor"]); _symbol(layers,"poi-labels-important",_MAP_DARK["poi_important"],halo_width=1.9); _symbol(layers,"poi-labels-food",_MAP_DARK["poi_food"],halo_width=1.8); _symbol(layers,"house-numbers",_MAP_DARK["label_minor"],halo_width=1.2)

def _paint(layers:dict[str|None,dict[str,Any]],layer_id:str,property_name:str,value:Any)->None:
    layer=layers.get(layer_id)
    if layer is not None: layer.setdefault("paint",{})[property_name]=value

def _symbol(layers:dict[str|None,dict[str,Any]],layer_id:str,text_color:str,*,halo_width:float=1.6)->None:
    layer=layers.get(layer_id)
    if layer is None:return
    paint=layer.setdefault("paint",{}); paint["text-color"]=text_color; paint["text-halo-color"]=_MAP_DARK["label_halo"]; paint["text-halo-width"]=halo_width
