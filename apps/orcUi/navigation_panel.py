# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Full navigation panel for the integrated ORC cockpit UI."""
from __future__ import annotations
import math
import os
import tkinter as tk
from collections.abc import Callable
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from ui.navigation import MapRequestHandlerIf

BG="#05090d"; PANEL="#0b1117"; BORDER="#25313b"; TEXT="#edf2f5"; MUTED="#89959e"; GREEN="#84ce1f"; BLUE="#168bd1"; RED="#f15a16"; PURPLE="#a25ce5"

class NavigationPanel(tk.Frame):
    def __init__(self,parent:tk.Misc,*,map_request_handler:MapRequestHandlerIf|None=None,on_back:Callable[[],None]|None=None)->None:
        super().__init__(parent,bg=BG); del on_back
        runtime=get_shared_map_camera_runtime(); self._request_handler=map_request_handler or runtime.request_handler
        self._earth_launcher=GoogleEarthLauncher(); self._earth_visible=False
        self._zoom_level=float(getattr(self._request_handler,"zoom_level",16.5)); self._pitch_rad=float(getattr(self._request_handler,"pitch_rad",math.radians(45.0)))
        self._follow_enabled=bool(getattr(self._request_handler,"follow_enabled",True)); self._poi_focus=set(getattr(self._request_handler,"poi_focus",())); self._build(); self._schedule_renderer_refresh()
    @property
    def map_host_window_id(self)->int: self.update_idletasks(); return self._map_host.winfo_id()
    def set_map_request_handler(self,handler:MapRequestHandlerIf|None)->None:
        if handler is not None: self._request_handler=handler
    def set_follow_enabled(self,enabled:bool)->None:
        self._follow_enabled=enabled; self._follow_button.configure(text="F" if enabled else "F̸",fg=GREEN if enabled else TEXT)
    def destroy(self)->None:
        if self._earth_launcher.is_running():
            self._earth_launcher.stop(self._display())
        super().destroy()
    def _build(self)->None:
        self.grid_rowconfigure(1,weight=1); self.grid_columnconfigure(0,weight=1)
        bar=tk.Frame(self,bg=BG,height=38); bar.grid(row=0,column=0,sticky="ew",pady=(0,4)); bar.grid_propagate(False)
        shortcuts=tk.Frame(bar,bg=BG); shortcuts.pack(side=tk.LEFT,padx=2,pady=3)
        for text,accent,key in (("⌂ HOME",BLUE,"home"),("▣ WORK",PURPLE,"work"),("⛽ GAS",RED,"gas"),("▣ GROCERY",GREEN,"grocery"),("♨ FOOD",RED,"food")):
            tk.Button(shortcuts,text=text,command=lambda s=key:self._destination_shortcut(s),bg=PANEL,fg=accent,activebackground="#101820",activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",8,"bold"),width=9,height=1,padx=3,pady=1).pack(side=tk.LEFT,padx=(0,4))
        self._shortcut_status=tk.StringVar(value=self._focus_status())
        self._earth_button=tk.Button(bar,text="◉  EARTH",command=self._toggle_earth,bg=BLUE,fg="#ffffff",activebackground=GREEN,activeforeground="#05090d",relief=tk.FLAT,highlightthickness=2,highlightbackground="#5bbcff",font=("Sans",9,"bold"),width=11,height=1,padx=5,pady=1)
        self._earth_button.pack(side=tk.RIGHT,padx=(7,2),pady=2)
        tk.Label(bar,textvariable=self._shortcut_status,bg=BG,fg=MUTED,font=("Sans",7),anchor="e").pack(side=tk.RIGHT,padx=5)
        self._body=tk.Frame(self,bg=BG); self._body.grid(row=1,column=0,sticky="nsew"); self._body.grid_rowconfigure(0,weight=1); self._body.grid_columnconfigure(0,weight=1)
        self._map_host=tk.Frame(self._body,bg="#020406",highlightthickness=1,highlightbackground=BORDER); self._map_host.grid(row=0,column=0,sticky="nsew")
        self._controls=tk.Frame(self._body,bg=PANEL,width=62); self._controls.grid(row=0,column=1,sticky="ns",padx=(4,0)); self._controls.grid_propagate(False)
        self._follow_button=self._control(self._controls,"F",self._toggle_follow,GREEN); self._follow_button.pack(fill=tk.X,padx=5,pady=(7,5)); self.set_follow_enabled(self._follow_enabled)
        pan=tk.Frame(self._controls,bg=PANEL); pan.pack(pady=2)
        for row,col,text,up,right in ((0,1,"▲",1,0),(1,0,"◀",0,-1),(1,2,"▶",0,1),(2,1,"▼",-1,0)):
            tk.Button(pan,text=text,command=lambda u=up,r=right:self._pan(u,r),bg="#101820",fg=TEXT,activebackground=BLUE,activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",9,"bold"),width=1,height=1,padx=2,pady=1).grid(row=row,column=col,padx=1,pady=1)
        for text,command,accent in (("+",lambda:self._change_zoom(1),BLUE),("−",lambda:self._change_zoom(-1),BLUE),("↗",lambda:self._change_pitch(5),PURPLE),("↘",lambda:self._change_pitch(-5),PURPLE),("N",self._north_up,TEXT),("◎",self._recenter,GREEN)):
            self._control(self._controls,text,command,accent).pack(fill=tk.X,padx=5,pady=2)
        tk.Label(self._controls,text="ZOOM\nTILT\nNORTH\nCENTER",bg=PANEL,fg=MUTED,font=("Sans",6),justify=tk.CENTER).pack(side=tk.BOTTOM,pady=5)
    def _control(self,parent,text,command,fg):
        return tk.Button(parent,text=text,command=command,bg=PANEL,fg=fg,activebackground="#101820",activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",11,"bold"),height=1)
    def _display(self)->str:
        return os.environ.get("DISPLAY",":1")
    def _set_earth_layout(self,enabled:bool)->None:
        if enabled:
            self._controls.grid_remove()
        else:
            self._controls.grid()
        self._body.update_idletasks()
    def _toggle_earth(self)->None:
        try:
            self._map_host.update_idletasks()
            if not self._earth_visible:
                self._set_earth_layout(True)
                position=(self._map_host.winfo_rootx(),self._map_host.winfo_rooty())
                size=(max(1,self._map_host.winfo_width()),max(1,self._map_host.winfo_height()))
                self._earth_launcher.configure_app_window(position=position,size=size)
                self._earth_launcher.set_color_scheme("dark" if self._is_dark_theme() else "light")
            self._earth_visible=self._earth_launcher.toggle(self._display())
            if self._earth_visible:
                self._earth_button.configure(text="▣  MAP",bg=GREEN,fg="#05090d",highlightbackground="#b8f55f")
            else:
                self._set_earth_layout(False)
                self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="#ffffff",highlightbackground="#5bbcff")
            self._shortcut_status.set("Google Earth" if self._earth_visible else "MapLibre")
        except (OSError,RuntimeError,ValueError) as exc:
            self._earth_visible=False; self._set_earth_layout(False); self._earth_button.configure(text="◉  EARTH",bg=RED,fg="#ffffff",highlightbackground="#ff8b5e"); self._shortcut_status.set(f"Earth unavailable: {exc}")
    def _is_dark_theme(self)->bool:
        color=BG.lstrip("#")
        red,green,blue=(int(color[index:index+2],16) for index in (0,2,4))
        return (red*299+green*587+blue*114)/1000 < 128
    def _schedule_renderer_refresh(self)->None:
        for delay_ms in (300,700,1200): self.after(delay_ms,self._refresh_renderer_state)
    def _refresh_renderer_state(self)->None:
        refresh=getattr(self._request_handler,"refresh_renderer_state",None)
        if refresh is not None: refresh()
    def _focus_status(self)->str:
        names=[]
        if "fuel" in self._poi_focus: names.append("Gas")
        if "grocery" in self._poi_focus: names.append("Grocery")
        return " + ".join(names)+" highlighted" if names else ""
    def _destination_shortcut(self,shortcut:str)->None:
        focus_category={"gas":"fuel","grocery":"grocery"}.get(shortcut)
        if focus_category is not None:
            if focus_category in self._poi_focus: self._poi_focus.remove(focus_category)
            else: self._poi_focus.add(focus_category)
            self._request_handler.request_poi_focus(focus_category)
            self._shortcut_status.set(self._focus_status()); return
        self._request_handler.request_poi_focus(None); self._poi_focus.clear()
        messages={"home":"Home location not configured","work":"Work location not configured","food":"Nearby food search not connected yet"}
        self._shortcut_status.set(messages[shortcut]); self.after(2500,lambda:self._shortcut_status.set(""))
    def _toggle_follow(self)->None:
        enabled=not self._follow_enabled; self.set_follow_enabled(enabled); self._request_handler.request_follow(enabled)
    def _pan(self,up:float,right:float)->None:
        self.set_follow_enabled(False); self._map_host.update_idletasks(); self._request_handler.request_pan_screen(right_px=right*max(48,self._map_host.winfo_width()*.25),up_px=up*max(48,self._map_host.winfo_height()*.25))
    def _change_zoom(self,delta:float)->None:
        self._zoom_level=max(1,min(22,self._zoom_level+delta)); self.set_follow_enabled(False); self._request_handler.request_zoom(self._zoom_level)
    def _change_pitch(self,delta_deg:float)->None:
        pitch_deg=max(0,min(60,math.degrees(self._pitch_rad)+delta_deg)); self._pitch_rad=math.radians(pitch_deg); self.set_follow_enabled(False); self._request_handler.request_pitch(self._pitch_rad)
    def _north_up(self)->None: self.set_follow_enabled(False); self._request_handler.request_bearing(0.0)
    def _recenter(self)->None: self.set_follow_enabled(True); self._request_handler.request_recenter()
