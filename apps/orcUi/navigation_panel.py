# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Full navigation panel for the integrated ORC cockpit UI."""
from __future__ import annotations
import math, os, tkinter as tk
from collections.abc import Callable
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from ui.navigation import MapRequestHandlerIf
BG="#05090d"; PANEL="#0b1117"; BORDER="#25313b"; TEXT="#edf2f5"; MUTED="#89959e"; GREEN="#84ce1f"; BLUE="#168bd1"; RED="#f15a16"; PURPLE="#a25ce5"
class NavigationPanel(tk.Frame):
 def __init__(self,parent:tk.Misc,*,map_request_handler:MapRequestHandlerIf|None=None,on_back:Callable[[],None]|None=None)->None:
  super().__init__(parent,bg=BG); del on_back; self._camera_runtime=get_shared_map_camera_runtime(); self._request_handler=map_request_handler or self._camera_runtime.request_handler; self._earth_launcher=GoogleEarthLauncher(); self._earth_visible=False; self._earth_initialized=False; self._zoom_level=float(getattr(self._request_handler,"zoom_level",16.5)); self._pitch_rad=float(getattr(self._request_handler,"pitch_rad",math.radians(45))); self._follow_enabled=bool(getattr(self._request_handler,"follow_enabled",True)); self._poi_focus=set(getattr(self._request_handler,"poi_focus",())); self._build(); self._schedule_renderer_refresh()
 @property
 def map_host_window_id(self)->int:self.update_idletasks();return self._map_host.winfo_id()
 def set_map_request_handler(self,h):
  if h is not None:self._request_handler=h
 def set_follow_enabled(self,e):self._follow_enabled=e;self._follow_button.configure(text="F" if e else "F̸",fg=GREEN if e else TEXT)
 def destroy(self):
  if self._earth_launcher.is_running():self._earth_launcher.stop(self._display())
  super().destroy()
 def _build(self):
  self.grid_rowconfigure(1,weight=1);self.grid_columnconfigure(0,weight=1);bar=tk.Frame(self,bg=BG,height=38);bar.grid(row=0,column=0,sticky="ew",pady=(0,4));bar.grid_propagate(False);short=tk.Frame(bar,bg=BG);short.pack(side=tk.LEFT,padx=2,pady=3)
  for text,accent,key in (("⌂ HOME",BLUE,"home"),("▣ WORK",PURPLE,"work"),("⛽ GAS",RED,"gas"),("▣ GROCERY",GREEN,"grocery"),("♨ FOOD",RED,"food")):tk.Button(short,text=text,command=lambda s=key:self._destination_shortcut(s),bg=PANEL,fg=accent,relief=tk.FLAT,font=("Sans",8,"bold"),width=9).pack(side=tk.LEFT,padx=(0,4))
  self._shortcut_status=tk.StringVar(value=self._focus_status());self._earth_button=tk.Button(bar,text="◉  EARTH",command=self._toggle_earth,bg=BLUE,fg="white",relief=tk.FLAT,font=("Sans",9,"bold"),width=11);self._earth_button.pack(side=tk.RIGHT,padx=(7,2),pady=2);tk.Label(bar,textvariable=self._shortcut_status,bg=BG,fg=MUTED,font=("Sans",7)).pack(side=tk.RIGHT,padx=5)
  self._body=tk.Frame(self,bg=BG);self._body.grid(row=1,column=0,sticky="nsew");self._body.grid_rowconfigure(0,weight=1);self._body.grid_columnconfigure(0,weight=1);self._map_host=tk.Frame(self._body,bg="#020406",highlightthickness=1,highlightbackground=BORDER);self._map_host.grid(row=0,column=0,sticky="nsew");self._controls=tk.Frame(self._body,bg=PANEL,width=62);self._controls.grid(row=0,column=1,sticky="ns",padx=(4,0));self._controls.grid_propagate(False);self._follow_button=self._control(self._controls,"F",self._toggle_follow,GREEN);self._follow_button.pack(fill=tk.X,padx=5,pady=7);self.set_follow_enabled(self._follow_enabled)
  for text,cmd in (("+",lambda:self._change_zoom(1)),("−",lambda:self._change_zoom(-1)),("N",self._north_up),("◎",self._recenter)):self._control(self._controls,text,cmd,TEXT).pack(fill=tk.X,padx=5,pady=3)
 def _control(self,p,t,c,f):return tk.Button(p,text=t,command=c,bg=PANEL,fg=f,relief=tk.FLAT,font=("Sans",11,"bold"))
 def _display(self):return os.environ.get("DISPLAY",":1")
 def _set_earth_layout(self,e):
  self._controls.grid_remove() if e else self._controls.grid();self._body.update_idletasks()
 def _prepare_first_earth_launch(self):
  if self._earth_initialized:return
  if self._earth_launcher.is_running():self._earth_launcher.stop(self._display())
  self._earth_launcher.set_color_scheme("dark");p=self._camera_runtime.latest_position
  if p is not None:
   lat=math.degrees(p.latitude_rad);lon=math.degrees(p.longitude_rad);self._earth_launcher.set_location(lat,lon);self._shortcut_status.set(f"Earth {lat:.5f}, {lon:.5f}")
  else:self._shortcut_status.set("Earth: waiting for GPS; using default")
  self._earth_initialized=True
 def _toggle_earth(self):
  try:
   if not self._earth_visible:
    self._set_earth_layout(True);self._prepare_first_earth_launch();self._map_host.update_idletasks();size=(max(1,self._map_host.winfo_width()),max(1,self._map_host.winfo_height()));self._earth_launcher.configure_app_window(position=(self._map_host.winfo_rootx(),self._map_host.winfo_rooty()),size=size,parent_window_id=self._map_host.winfo_id())
   self._earth_visible=self._earth_launcher.toggle(self._display())
   if self._earth_visible:self._earth_button.configure(text="▣  MAP",bg=GREEN,fg=BG)
   else:self._set_earth_layout(False);self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="white");self._shortcut_status.set("MapLibre")
  except Exception as exc:self._earth_visible=False;self._set_earth_layout(False);self._shortcut_status.set(f"Earth unavailable: {exc}")
 def _schedule_renderer_refresh(self):
  for d in (300,700,1200):self.after(d,self._refresh_renderer_state)
 def _refresh_renderer_state(self):
  f=getattr(self._request_handler,"refresh_renderer_state",None)
  if f:f()
 def _focus_status(self):return ""
 def _destination_shortcut(self,s):self._shortcut_status.set(f"{s.title()} shortcut")
 def _toggle_follow(self):self.set_follow_enabled(not self._follow_enabled);self._request_handler.request_follow(self._follow_enabled)
 def _change_zoom(self,d):self._zoom_level+=d;self._request_handler.request_zoom(self._zoom_level)
 def _north_up(self):self._request_handler.request_bearing(0.0)
 def _recenter(self):self.set_follow_enabled(True);self._request_handler.request_recenter()
