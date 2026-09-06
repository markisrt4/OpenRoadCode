# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Full navigation panel for the integrated ORC cockpit UI."""
from __future__ import annotations
import math, os, tkinter as tk
from collections.abc import Callable
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_input_camera_controller import EarthInputCameraController
from frontends.x11 import X11WindowEmbedder
from ui.navigation import MapRequestHandlerIf

BG="#05090d"; PANEL="#0b1117"; BORDER="#25313b"; TEXT="#edf2f5"; MUTED="#89959e"; GREEN="#84ce1f"; BLUE="#168bd1"; RED="#f15a16"; PURPLE="#a25ce5"
_MPS_TO_MPH=2.2369362920544
_M_TO_MI=0.000621371192237334
_M_TO_FT=3.28083989501312
_EARTH_POSITION_THRESHOLD_M=3.0
_EARTH_RADIUS_M=6371008.8

class NavigationPanel(tk.Frame):
 def __init__(self,parent:tk.Misc,*,map_request_handler:MapRequestHandlerIf|None=None,on_back:Callable[[],None]|None=None)->None:
  super().__init__(parent,bg=BG); del on_back
  self._camera_runtime=get_shared_map_camera_runtime(); self._request_handler=map_request_handler or self._camera_runtime.request_handler
  self._earth_launcher=GoogleEarthLauncher(); self._earth_embedder=X11WindowEmbedder(); self._earth_geolocation=EarthGeolocationBridge(); self._earth_input=EarthInputCameraController(); self._earth_visible=False; self._earth_initialized=False; self._earth_hud_after:str|None=None; self._earth_last_sent_position:tuple[float,float]|None=None; self._earth_watch_count=0; self._earth_tracking_primed=False; self._earth_follow_enabled=True
  self._zoom_level=float(getattr(self._request_handler,"zoom_level",16.5)); self._pitch_rad=float(getattr(self._request_handler,"pitch_rad",math.radians(45))); self._follow_enabled=bool(getattr(self._request_handler,"follow_enabled",True)); self._poi_focus=set(getattr(self._request_handler,"poi_focus",()))
  self._build(); self._schedule_renderer_refresh()
 @property
 def map_host_window_id(self)->int:self.update_idletasks();return int(self._map_host.winfo_id())
 def set_map_request_handler(self,h):
  if h is not None:self._request_handler=h
 def set_follow_enabled(self,e):self._follow_enabled=e;self._update_follow_button()
 def _update_follow_button(self):
  enabled=self._earth_follow_enabled if self._earth_visible else self._follow_enabled
  self._follow_button.configure(text="F" if enabled else "F̸",fg=GREEN if enabled else TEXT)
 def destroy(self):
  self._stop_earth_hud(); self._detach_earth()
  if self._earth_launcher.is_running():self._earth_launcher.stop(self._display())
  super().destroy()
 def _build(self):
  self.grid_rowconfigure(1,weight=1);self.grid_columnconfigure(0,weight=1)
  bar=tk.Frame(self,bg=BG,height=38);bar.grid(row=0,column=0,sticky="ew",pady=(0,4));bar.grid_propagate(False)
  short=tk.Frame(bar,bg=BG)
  for text,accent,key in (("⌂ HOME",BLUE,"home"),("▣ WORK",PURPLE,"work"),("⛽ GAS",RED,"gas"),("▣ GROCERY",GREEN,"grocery"),("♨ FOOD",RED,"food")):tk.Button(short,text=text,command=lambda s=key:self._destination_shortcut(s),bg=PANEL,fg=accent,relief=tk.FLAT,font=("Sans",8,"bold"),width=9).pack(side=tk.LEFT,padx=(0,4))
  self._shortcut_status=tk.StringVar(value=self._focus_status());self._earth_button=tk.Button(bar,text="◉  EARTH",command=self._toggle_earth,bg=BLUE,fg="white",relief=tk.FLAT,font=("Sans",9,"bold"),width=11);self._earth_button.pack(side=tk.RIGHT,padx=(7,2),pady=2);tk.Label(bar,textvariable=self._shortcut_status,bg=BG,fg=MUTED,font=("Sans",7)).pack(side=tk.RIGHT,padx=5);short.pack(side=tk.LEFT,padx=2,pady=3)
  self._body=tk.Frame(self,bg=BG);self._body.grid(row=1,column=0,sticky="nsew");self._body.grid_rowconfigure(0,weight=1);self._body.grid_columnconfigure(0,weight=1)
  self._map_host=tk.Frame(self._body,bg="#020406",highlightthickness=1,highlightbackground=BORDER);self._map_host.grid(row=0,column=0,sticky="nsew");self._map_host.bind("<Configure>",self._on_map_host_resize)
  self._controls=tk.Frame(self._body,bg=PANEL,width=62);self._controls.grid(row=0,column=1,rowspan=3,sticky="ns",padx=(4,0));self._controls.grid_propagate(False);self._follow_button=self._control(self._controls,"F",self._toggle_follow,GREEN);self._follow_button.pack(fill=tk.X,padx=5,pady=7);self.set_follow_enabled(self._follow_enabled)
  for text,cmd in (("+",lambda:self._change_zoom(1)),("−",lambda:self._change_zoom(-1)),("N",self._north_up),("◎",self._recenter)):self._control(self._controls,text,cmd,TEXT).pack(fill=tk.X,padx=5,pady=3)
  self._earth_guidance=tk.Frame(self._body,bg=PANEL,highlightthickness=1,highlightbackground=BORDER);self._earth_instruction_var=tk.StringVar(value="No active route");self._earth_maneuver_distance_var=tk.StringVar(value="");self._earth_route_remaining_var=tk.StringVar(value="")
  tk.Label(self._earth_guidance,text="➜",bg=PANEL,fg=GREEN,font=("Sans",18,"bold"),padx=10).pack(side=tk.LEFT);tk.Label(self._earth_guidance,textvariable=self._earth_instruction_var,bg=PANEL,fg=TEXT,font=("Sans",11,"bold"),anchor="w").pack(side=tk.LEFT,fill=tk.X,expand=True,pady=5);tk.Label(self._earth_guidance,textvariable=self._earth_maneuver_distance_var,bg=PANEL,fg=GREEN,font=("Sans",10,"bold"),padx=10).pack(side=tk.RIGHT);tk.Label(self._earth_guidance,textvariable=self._earth_route_remaining_var,bg=PANEL,fg=MUTED,font=("Sans",8),padx=8).pack(side=tk.RIGHT)
  self._earth_hud=tk.Frame(self._body,bg=PANEL,highlightthickness=1,highlightbackground=BORDER);self._earth_speed_var=tk.StringVar(value="-- mph");self._earth_track_var=tk.StringVar(value="---°");self._earth_position_var=tk.StringVar(value="GPS --")
  tk.Label(self._earth_hud,text="EARTH",bg=PANEL,fg=BLUE,font=("Sans",8,"bold"),padx=9,pady=5).pack(side=tk.LEFT);tk.Label(self._earth_hud,textvariable=self._earth_speed_var,bg=PANEL,fg=GREEN,font=("Sans",11,"bold"),padx=10).pack(side=tk.LEFT);tk.Label(self._earth_hud,textvariable=self._earth_track_var,bg=PANEL,fg=TEXT,font=("Sans",9,"bold"),padx=10).pack(side=tk.LEFT);tk.Label(self._earth_hud,textvariable=self._earth_position_var,bg=PANEL,fg=MUTED,font=("Monospace",8),padx=10).pack(side=tk.RIGHT)
 def _control(self,p,t,c,f):return tk.Button(p,text=t,command=c,bg=PANEL,fg=f,relief=tk.FLAT,font=("Sans",11,"bold"))
 def _display(self):return os.environ.get("DISPLAY",":1")
 def _prepare_first_earth_launch(self):
  if self._earth_initialized:return
  if self._earth_launcher.is_running():self._earth_launcher.stop(self._display())
  self._earth_launcher.set_color_scheme("dark");p=self._camera_runtime.latest_position
  if p is not None:
   lat=math.degrees(p.latitude_rad);lon=math.degrees(p.longitude_rad);self._earth_launcher.set_location(lat,lon);self._shortcut_status.set(f"Earth {lat:.5f}, {lon:.5f}")
  else:self._shortcut_status.set("Earth: waiting for GPS; using default")
  self._earth_initialized=True
 def _earth_geometry(self)->tuple[tuple[int,int],tuple[int,int]]:
  self.update_idletasks();return (self._map_host.winfo_rootx(),self._map_host.winfo_rooty()),(max(1,self._map_host.winfo_width()),max(1,self._map_host.winfo_height()))
 def _embed_earth(self)->None:
  self._earth_guidance.grid(row=1,column=0,sticky="ew",pady=(4,0));self._earth_hud.grid(row=2,column=0,sticky="ew",pady=(3,0));self.update_idletasks();position,size=self._earth_geometry()
  if not self._earth_launcher.is_running():self._earth_launcher.configure_app_window(position=position,size=size);self._earth_launcher.launch(self._display())
  self.update_idletasks();self._earth_embedder.embed(0,self.map_host_window_id,size[0],size[1],window_class=GoogleEarthLauncher.WINDOW_CLASS)
  self._earth_last_sent_position=None;self._earth_watch_count=0;self._earth_tracking_primed=False;self._earth_follow_enabled=True;self._earth_geolocation.install();self._earth_visible=True;self._earth_button.configure(text="▣  MAP",bg=GREEN,fg=BG);self._update_follow_button();self._start_earth_hud()
 def _detach_earth(self)->None:
  if self._earth_embedder.window_id is not None:
   try:self._earth_embedder.detach(int(self.winfo_toplevel().winfo_id()))
   except (OSError,RuntimeError):pass
  self._earth_embedder.clear()
 def _leave_earth(self)->None:
  self._stop_earth_hud();self._detach_earth();self._earth_guidance.grid_remove();self._earth_hud.grid_remove();self._earth_visible=False;self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="white");self._update_follow_button();self._shortcut_status.set("MapLibre")
 def _toggle_earth(self):
  try:
   if self._earth_visible:self._leave_earth();return
   self._prepare_first_earth_launch();self._embed_earth()
  except Exception as exc:
   self._earth_visible=False;self._stop_earth_hud();self._detach_earth();self._earth_guidance.grid_remove();self._earth_hud.grid_remove()
   if self._earth_launcher.is_running():
    try:self._earth_launcher.stop(self._display())
    except Exception:pass
   self._earth_initialized=False;self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="white");self._update_follow_button();self._shortcut_status.set(f"Earth unavailable: {exc}")
 def _start_earth_hud(self)->None:
  self._stop_earth_hud();self._update_earth_hud()
 def _stop_earth_hud(self)->None:
  if self._earth_hud_after is not None:
   try:self.after_cancel(self._earth_hud_after)
   except tk.TclError:pass
   self._earth_hud_after=None
 def _refresh_earth_tracking_watch(self)->None:
  if not self._earth_follow_enabled:return
  if not self._earth_geolocation.install():return
  count=self._earth_geolocation.registration_count()
  if count is None:return
  if count>self._earth_watch_count:
   self._earth_watch_count=count;self._earth_tracking_primed=False;self._earth_last_sent_position=None
  if count>0 and not self._earth_tracking_primed:
   if self._send_earth_position(force=True):self._earth_tracking_primed=True;self._shortcut_status.set("Earth GPS tracking active")
 def _send_earth_position(self,*,force:bool=False)->bool:
  if not self._earth_follow_enabled:return False
  position=self._camera_runtime.latest_position
  if position is None:return False
  speed=self._camera_runtime.latest_ground_speed_m_s;track=self._camera_runtime.latest_track_rad;lat=math.degrees(position.latitude_rad);lon=math.degrees(position.longitude_rad)
  if not force and not self._earth_position_changed(lat,lon):return False
  if self._earth_geolocation.push_position(lat,lon,heading_deg=None if track is None else math.degrees(track)%360.0,speed_m_s=None if speed is None else max(0.0,speed)):
   self._earth_last_sent_position=(lat,lon);return True
  self._shortcut_status.set("Earth GPS bridge unavailable");return False
 def _update_earth_hud(self)->None:
  if not self._earth_visible:return
  speed=self._camera_runtime.latest_ground_speed_m_s;track=self._camera_runtime.latest_track_rad;position=self._camera_runtime.latest_position
  self._earth_speed_var.set("-- mph" if speed is None else f"{max(0.0,speed)*_MPS_TO_MPH:.0f} mph")
  if track is None:self._earth_track_var.set("---°")
  else:self._earth_track_var.set(f"{math.degrees(track)%360.0:03.0f}° {self._cardinal(track)}")
  if position is None:self._earth_position_var.set("GPS --")
  else:
   lat=math.degrees(position.latitude_rad);lon=math.degrees(position.longitude_rad);self._earth_position_var.set(f"{lat:.4f}, {lon:.4f}")
  self._refresh_earth_tracking_watch()
  if self._earth_tracking_primed:self._send_earth_position()
  self._update_earth_guidance();self._earth_hud_after=self.after(500,self._update_earth_hud)
 def _earth_position_changed(self,lat:float,lon:float)->bool:
  previous=self._earth_last_sent_position
  if previous is None:return True
  lat1,lon1=map(math.radians,previous);lat2,lon2=math.radians(lat),math.radians(lon)
  dlat=lat2-lat1;dlon=lon2-lon1
  a=math.sin(dlat/2.0)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2.0)**2
  distance=_EARTH_RADIUS_M*2.0*math.atan2(math.sqrt(a),math.sqrt(max(0.0,1.0-a)))
  return distance>=_EARTH_POSITION_THRESHOLD_M
 def _update_earth_guidance(self)->None:
  if self._camera_runtime.latest_route_complete:self._earth_instruction_var.set("Destination reached");self._earth_maneuver_distance_var.set("");self._earth_route_remaining_var.set("");return
  instruction=self._camera_runtime.latest_instruction
  if self._camera_runtime.latest_off_route:self._earth_instruction_var.set("OFF ROUTE" if not instruction else f"OFF ROUTE  •  {instruction}")
  else:self._earth_instruction_var.set(instruction or "No active route")
  self._earth_maneuver_distance_var.set(self._format_distance(self._camera_runtime.latest_distance_to_maneuver_m));remaining=self._camera_runtime.latest_distance_remaining_m;self._earth_route_remaining_var.set("" if remaining is None else f"{remaining*_M_TO_MI:.1f} mi remaining")
 @staticmethod
 def _format_distance(distance_m:float|None)->str:
  if distance_m is None:return ""
  if distance_m<304.8:return f"{max(0.0,distance_m)*_M_TO_FT:.0f} ft"
  return f"{max(0.0,distance_m)*_M_TO_MI:.1f} mi"
 @staticmethod
 def _cardinal(track_rad:float)->str:
  names=("N","NE","E","SE","S","SW","W","NW");return names[int((math.degrees(track_rad)%360.0+22.5)//45.0)%8]
 def _on_map_host_resize(self,event):
  if self._earth_visible:self._earth_embedder.resize(max(1,event.width),max(1,event.height))
 def _schedule_renderer_refresh(self):
  for d in (300,700,1200):self.after(d,self._refresh_renderer_state)
 def _refresh_renderer_state(self):
  f=getattr(self._request_handler,"refresh_renderer_state",None)
  if f:f()
 def _focus_status(self):return ""
 def _destination_shortcut(self,s):self._shortcut_status.set(f"{s.title()} shortcut")
 def _toggle_follow(self):
  if self._earth_visible:
   self._earth_follow_enabled=not self._earth_follow_enabled
   if self._earth_follow_enabled:
    self._earth_tracking_primed=False;self._earth_last_sent_position=None;self._refresh_earth_tracking_watch();self._shortcut_status.set("Earth follow on")
   else:self._shortcut_status.set("Earth follow off")
   self._update_follow_button();return
  self.set_follow_enabled(not self._follow_enabled);self._request_handler.request_follow(self._follow_enabled)
 def _change_zoom(self,d):
  if self._earth_visible:
   ok=self._earth_input.zoom_in() if d>0 else self._earth_input.zoom_out();self._shortcut_status.set("Earth zoom" if ok else "Earth zoom unavailable");return
  self._zoom_level+=d;self._request_handler.request_zoom(self._zoom_level)
 def _north_up(self):
  if self._earth_visible:
   self._shortcut_status.set("Earth north up" if self._earth_input.north_up() else "Earth north-up unavailable");return
  self._request_handler.request_bearing(0.0)
 def _recenter(self):
  if self._earth_visible:
   self._earth_follow_enabled=True;self._earth_tracking_primed=False;self._earth_last_sent_position=None;self._update_follow_button()
   if self._send_earth_position(force=True):self._earth_tracking_primed=True;self._shortcut_status.set("Earth recentered")
   else:self._shortcut_status.set("Earth recenter waiting for GPS")
   return
  self.set_follow_enabled(True);self._request_handler.request_recenter()
