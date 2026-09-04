# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared ORC UI theme palette and MapLibre style adaptation."""
from __future__ import annotations
import json
import tkinter as tk
from pathlib import Path
from typing import Any

from ui.theme import ThemeMode

DARK={"bg":"#05090d","panel":"#0b1117","top":"#020406","nav":"#070c11","active":"#101820","border":"#25313b","text":"#edf2f5","muted":"#89959e"}
LIGHT={"bg":"#e8edf0","panel":"#f6f8f9","top":"#dce3e7","nav":"#e1e7ea","active":"#d1dbe0","border":"#b3c0c7","text":"#20282d","muted":"#66747c"}
ACCENT_BLUE="#168bd1"; ACCENT_GREEN="#84ce1f"; ACCENT_RED="#f15a16"; ACCENT_PURPLE="#a25ce5"; ACCENT_YELLOW="#d6ad22"
_LIGHT_BLUE="#0878b6"; _LIGHT_GREEN="#5f9418"; _LIGHT_RED="#c94d1a"; _LIGHT_PURPLE="#7f49ad"; _LIGHT_YELLOW="#927518"
_DARK_TO_LIGHT={"#05090d":LIGHT["bg"],"#0b1117":LIGHT["panel"],"#020406":LIGHT["top"],"#070c11":LIGHT["nav"],"#101820":LIGHT["active"],"#25313b":LIGHT["border"],"#edf2f5":LIGHT["text"],"#89959e":LIGHT["muted"],ACCENT_BLUE:_LIGHT_BLUE,ACCENT_GREEN:_LIGHT_GREEN,ACCENT_RED:_LIGHT_RED,ACCENT_PURPLE:_LIGHT_PURPLE,ACCENT_YELLOW:_LIGHT_YELLOW}

# Automotive instruments are canvas-heavy, so normal Tk widget option
# translation is not enough. Keep the performance-cluster character in dark
# mode while supplying a deliberate daylight palette instead of literal color
# inversion. These entries also cover the off-road dashboard's semantic colors.
_DARK_TO_LIGHT.update({
    "#000000":"#e8edf0",
    "#090a0b":"#eef2f4",
    "#08090a":"#e7ecef",
    "#0a0c0d":"#f5f7f8",
    "#0b0d0e":"#f5f7f8",
    "#111315":"#ffffff",
    "#151719":"#d4dce0",
    "#17191b":"#20282d",
    "#181b1c":"#edf1f3",
    "#1e2123":"#cbd3d7",
    "#202326":"#aab5bb",
    "#282b2d":"#c4cdd2",
    "#2c2e2f":"#d6dde0",
    "#2e3133":"#bcc7cc",
    "#303234":"#c3cbd0",
    "#39484f":"#c0cbd0",
    "#4e3d12":"#ead9a8",
    "#57131b":"#f0c9cd",
    "#5e6263":"#aebbc1",
    "#626668":"#aebbc1",
    "#686b6d":"#66747c",
    "#6f7373":"#aeb8bd",
    "#707476":"#939fa5",
    "#747879":"#738189",
    "#767a7c":"#9aa5aa",
    "#7b1017":"#b94b53",
    "#85898a":"#7e8b92",
    "#8a8881":"#6d787e",
    "#9b9c99":"#c6ced2",
    "#9da1a2":"#9aa6ac",
    "#a92b34":"#c95b63",
    "#a9acad":"#6f7e86",
    "#aeb1b1":"#586970",
    "#b7b9b8":"#6e7b81",
    "#c7c9c7":"#9aa6ac",
    "#c8cbca":"#435159",
    "#d8dad9":"#35444b",
    "#d9dbd9":"#35444b",
    "#dedfda":"#f8fafb",
    "#e3e4e1":"#ffffff",
    "#f0f0ed":"#20282d",
    "#f2efe5":"#f8fafb",
    "#ffffff":"#20282d",
    "#ff694f":"#c73d2d",
    "#ff3143":"#d51f2b",
    "#ff3446":"#d51f2b",
    "#f0b323":"#9b720c",
    "#e4a514":"#9b720c",
    "#c88b0d":"#8b6508",
    "#760d14":"#b21f29",
    "#f26a70":"#d85d64",
    "#650008":"#9a3038",
    "#e10d1c":"#c81d2b",
    "#ff4b56":"#d94b55",
    "#c40012":"#b71927",
    "#07100d":"#e8edf0",
    "#101d18":"#f6f8f9",
    "#274238":"#b3c0c7",
    "#e5f2e9":"#20282d",
    "#8ca398":"#66747c",
    "#66e38f":"#5f9418",
    "#ffb347":"#927518",
    "#ff5d52":"#c94d1a",
    "#18344b":"#b9d9ea",
    "#493825":"#d8c4a8",
    "#263d31":"#d4ded8",
    "#355442":"#c4d3ca",
    "#1c322a":"#c5d0ca",
    "#274536":"#cbd8d0",
    "#102636":"#d2e3ec",
    "#7ea3b8":"#64869a",
    "#0a1512":"#eef2f0",
    "#193027":"#d3ddd7",
    "#27483a":"#c2d1c8",
    "#111613":"#ccd3cf",
    "#80958a":"#71827a",
    "#9bad9f":"#76867d",
    "#ffe6a1":"#d6ad22",
    "#b9c8bf":"#82928a",
    "#101411":"#c9d0cc",
    "#5b1512":"#f1d1cc",
    "#ffd6d2":"#7e332c",
})
# Games-specific light-mode mappings.
_DARK_TO_LIGHT.update({
    "#17300f":"#dcebcf",
    "#214019":"#cfdfc2",
    "#18232c":"#c7d2d8",
    "#102018":"#e2ecd9",
    "#0d1b24":"#dceaf2",
    "#11161a":"#e1e6e9",
    "#183024":"#d4e5c8",
    "#29110d":"#f6ded8",
    "#3b1811":"#edcfc7",
})

_LIGHT_TO_DARK={v:k for k,v in _DARK_TO_LIGHT.items()}

_MAP_DARK={
"background":"#0b151b","wood":"#164a35","grass":"#28523a","scrub":"#314b3b","farmland":"#3b5140",
"land_default":"#17262d","residential":"#22343d","commercial":"#40334d","industrial":"#33444a","cemetery":"#24513b","hospital":"#4b3349","school":"#354b52","landuse_default":"#293940","park":"#17613b",
"water":"#075078","waterway":"#21b8ed","boundary":"#73858e","rail":"#718087","path":"#7b898f","service_casing":"#39484f","service":"#718087","residential_casing":"#46565d","residential_road":"#8d9ba1","secondary_casing":"#275e78","secondary_road":"#73b7d8","primary_casing":"#075d8d","primary_road":"#31ace9","motorway_casing":"#034c79","motorway":"#00a9ff","aeroway":"#75848b","building":"#3b494f","building_outline":"#596970","route_casing":"#ffffff","route":"#ff4935","label":"#e1e9ec","label_major":"#ffffff","label_minor":"#c5d0d5","label_halo":"#081116","water_label":"#76ddff","road_ref":"#b1e3f5","poi":"#bfff55","poi_food":"#ff7448","house":"#a8b6bc"}
_MAP_LIGHT={
"background":"#e7eef2","wood":"#a9d4b8","grass":"#c8e3b2","scrub":"#d1e1c3","farmland":"#dce6b4","land_default":"#e1e8e8","residential":"#e1e7eb","commercial":"#eddbe7","industrial":"#d9e2e5","cemetery":"#c5dfcb","hospital":"#efd7e2","school":"#dce8df","landuse_default":"#dee6e7","park":"#a9dcb7","water":"#75bee3","waterway":"#2da6df","boundary":"#82949e","rail":"#8b989e","path":"#a1acae","service_casing":"#b9c3c7","service":"#f2f5f6","residential_casing":"#b1bdc3","residential_road":"#ffffff","secondary_casing":"#70a5bc","secondary_road":"#c1e2f1","primary_casing":"#277fae","primary_road":"#62b8e2","motorway_casing":"#146e9f","motorway":"#269bd4","aeroway":"#a1adb2","building":"#c6d1d6","building_outline":"#9eacb3","route_casing":"#ffffff","route":"#e33b24","label":"#2e3d45","label_major":"#17252c","label_minor":"#52636c","label_halo":"#f5f8f9","water_label":"#146f9f","road_ref":"#205f80","poi":"#477f12","poi_food":"#c54226","house":"#697980"}

def palette(mode:ThemeMode)->dict[str,str]: return DARK if mode is ThemeMode.DARK else LIGHT
def toggle(mode:ThemeMode)->ThemeMode: return ThemeMode.LIGHT if mode is ThemeMode.DARK else ThemeMode.DARK
def toggle_label(mode:ThemeMode)->str: return "☀  LIGHT" if mode is ThemeMode.DARK else "☾  DARK"
def apply_tk_theme(root:tk.Misc,mode:ThemeMode)->None: _apply_widget(root,_DARK_TO_LIGHT if mode is ThemeMode.LIGHT else _LIGHT_TO_DARK)
def install_map_style(mode:ThemeMode,data_root:str|Path|None=None)->Path|None:
    repo_root=Path(__file__).resolve().parents[2]; template=repo_root/"tools"/"map_builder"/"templates"/"openroadcode-style.json"; root=Path(data_root or Path.home()/".local"/"share"/"openroadcode"); destination=root/"maps"/"styles"/"openroadcode.json"
    if not template.is_file() or not destination.parent.is_dir(): return None
    document=json.loads(template.read_text(encoding="utf-8")); _apply_map_palette(document,_MAP_DARK if mode is ThemeMode.DARK else _MAP_LIGHT); destination.write_text(json.dumps(document,separators=(",",":")),encoding="utf-8"); return destination

def _apply_widget(widget:tk.Misc,mapping:dict[str,str])->None:
    for option in ("background","foreground","activebackground","activeforeground","highlightbackground","highlightcolor","insertbackground","selectbackground","selectforeground"):
        try: current=str(widget.cget(option)).lower()
        except (tk.TclError,AttributeError): continue
        if current in mapping:
            try: widget.configure(**{option:mapping[current]})
            except tk.TclError: pass
    if isinstance(widget,tk.Canvas): _apply_canvas_items(widget,mapping)
    for child in widget.winfo_children(): _apply_widget(child,mapping)

def _apply_canvas_items(canvas:tk.Canvas,mapping:dict[str,str])->None:
    """Translate colors already painted into a canvas.

    Vehicle instruments and the off-road dashboard draw most of their visual
    state as canvas items, so changing only the Canvas widget background would
    leave a dark dashboard floating in a light shell.
    """
    for item in canvas.find_all():
        for option in ("fill","outline"):
            try: current=str(canvas.itemcget(item,option)).lower()
            except tk.TclError: continue
            if current in mapping:
                try: canvas.itemconfigure(item,**{option:mapping[current]})
                except tk.TclError: pass

def _apply_map_palette(document:dict[str,Any],colors:dict[str,str])->None:
    layers={layer.get("id"):layer for layer in document.get("layers",[])}
    _paint(layers,"background","background-color",colors["background"])
    _paint(layers,"landcover","fill-color",["match",["get","class"],"wood",colors["wood"],"grass",colors["grass"],"scrub",colors["scrub"],"farmland",colors["farmland"],colors["land_default"]])
    _paint(layers,"landuse","fill-color",["match",["get","class"],"residential",colors["residential"],"commercial",colors["commercial"],"industrial",colors["industrial"],"cemetery",colors["cemetery"],"hospital",colors["hospital"],"school",colors["school"],colors["landuse_default"]])
    for lid,prop,key in (("parks","fill-color","park"),("water","fill-color","water"),("waterways","line-color","waterway"),("boundaries","line-color","boundary"),("railways","line-color","rail"),("paths","line-color","path"),("service-roads-casing","line-color","service_casing"),("service-roads","line-color","service"),("residential-roads-casing","line-color","residential_casing"),("residential-roads","line-color","residential_road"),("secondary-roads-casing","line-color","secondary_casing"),("secondary-roads","line-color","secondary_road"),("primary-roads-casing","line-color","primary_casing"),("primary-roads","line-color","primary_road"),("motorways-casing","line-color","motorway_casing"),("motorways","line-color","motorway"),("aeroways","line-color","aeroway"),("buildings","fill-color","building"),("buildings","fill-outline-color","building_outline"),("route-line-casing","line-color","route_casing"),("route-line","line-color","route")): _paint(layers,lid,prop,colors[key])
    _paint(layers,"primary-roads-casing","line-width",5.5); _paint(layers,"primary-roads","line-width",4.5)
    _paint(layers,"motorways-casing","line-width",6.5); _paint(layers,"motorways","line-width",5)
    for lid,key in (("water-labels","water_label"),("road-refs-major","road_ref"),("road-labels","label"),("place-labels","label_major"),("aerodrome-labels","label_minor"),("mountain-peaks","label_minor"),("poi-labels-important","poi"),("poi-labels-food","poi_food"),("house-numbers","house")): _paint_label(layers,lid,colors[key],colors["label_halo"])
def _paint_label(layers,layer_id,text_color,halo_color): _paint(layers,layer_id,"text-color",text_color); _paint(layers,layer_id,"text-halo-color",halo_color)
def _paint(layers,layer_id,property_name,value):
    layer=layers.get(layer_id)
    if layer is not None: layer.setdefault("paint",{})[property_name]=value
