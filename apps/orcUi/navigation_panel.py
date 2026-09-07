# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Full navigation panel for the integrated ORC cockpit UI."""
from __future__ import annotations
import math, os, tkinter as tk
from collections.abc import Callable
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.earth_map_button_overlay import EarthMapButtonOverlay
from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from controllers.navigation.earth_chase_camera_controller import EarthChaseCameraController
from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_input_camera_controller import EarthInputCameraController
from controllers.navigation.earth_vehicle_overlay import EarthVehicleOverlay
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
  self._earth_launcher=GoogleEarthLauncher(); self._earth_embedder=X11WindowEmbedder(); self._earth_geolocation=EarthGeolocationBridge(); self._earth_input=EarthInputCameraController(); self._earth_chase=EarthChaseCameraController(self._earth_input); self._earth_vehicle=EarthVehicleOverlay(); self._earth_visible=False; self._earth_initialized=False; self._earth_hud_after:str|None=None; self._earth_last_sent_position:tuple[float,float]|None=None; self._earth_watch_count=0; self._earth_tracking_primed=False; self._earth_follow_enabled=True; self._earth_menu_visible=True
  self._zoom_level=float(getattr(self._request_handler,"zoom_level",16.5)); self._pitch_rad=float(getattr(self._request_handler,"pitch_rad",math.radians(45))); self._follow_enabled=bool(getattr(self._request_handler,"follow_enabled",True)); self._poi_focus=set(getattr(self._request_handler,"poi_focus",()))
  self._build(); self._earth_map_overlay=EarthMapButtonOverlay(self,self._map_host,self._toggle_earth); self._schedule_renderer_refresh()
 @property
 def map_host_window_id(self)->int:self.update_idletasks();return int(self._map_host.winfo_id())
 def set_map_request_handler(self,h):
  if h is not None:self._request_handler=h
 def set_follow_enabled(self,e):self._follow_enabled=e;self._update_follow_button()
 def _update_follow_button(self):
  enabled=self._earth_follow_enabled if self._earth_visible else self._follow_enabled
  self._follow_button.configure(text="F" if enabled else "F̸",fg=GREEN if enabled else TEXT)
 def _update_chase_button(self):
  self._chase_button.configure(text="C" if self._earth_chase.enabled else "C̸",fg=GREEN if self._earth_chase.enabled else TEXT)
 def _update_menu_button(self):
  self._menu_button.configure(text="M" if self._earth_menu_visible else "M̸",fg=BLUE if self._earth_menu_visible else TEXT)
 def destroy(self):
  self._stop_earth_hud(); self._earth_map_overlay.destroy(); self._earth_vehicle.remove(); self._detach_earth()
  if self._earth_launcher.is_running():self._earth_launcher.stop(self._display())
  super().destroy()
 def _build(self):
  self.grid_rowconfigure(1,weight=1);self.grid_columnconfigure(0,weight=1)
  self._bar=tk.Frame(self,bg=BG,height=38);self._bar.grid(row=0,column=0,sticky="ew",pady=(0,4));self._bar.grid_propagate(False)
  self._shortcuts=tk.Frame(self._bar,bg=BG)
  for text,accent,key in (("⌂ HOME",BLUE,"home"),("▣ WORK",PURPLE,"work"),("⛽ GAS",RED,"gas"),("▣ GROCERY",GREEN,"grocery"),("♨ FOOD",RED,"food")):tk.Button(self._shortcuts,text=text,command=lambda s=key:self._destination_shortcut(s),bg=PANEL,fg=accent,relief=tk.FLAT,font=("Sans",8,"bold"),width=9).pack(side=tk.LEFT,padx=(0,4))
  self._shortcut_status=tk.StringVar(value=self._focus_status());self._earth_button=tk.Button(self._bar,text="◉  EARTH",command=self._toggle_earth,bg=BLUE,fg="white",relief=tk.FLAT,font=("Sans",9,"bold"),width=11);self._earth_button.pack(side=tk.RIGHT,padx=(7,2),pady=2);self._status_label=tk.Label(self._bar,textvariable=self._shortcut_status,bg=BG,fg=MUTED,font=("Sans",7));self._status_label.pack(side=tk.RIGHT,padx=5);self._shortcuts.pack(side=tk.LEFT,padx=2,pady=3)
  self._body=tk.Frame(self,bg=BG);self._body.grid(row=1,column=0,sticky="nsew");self._body.grid_rowconfigure(0,weight=1);self._body.grid_columnconfigure(0,weight=1)
  self._map_host=tk.Frame(self._body,bg="#020406",highlightthickness=1,highlightbackground=BORDER);self._map_host.grid(row=0,column=0,sticky="nsew");self._map_host.bind("<Configure>",self._on_map_host_resize)
  self._controls=tk.Frame(self._body,bg=PANEL,width=62);self._controls.grid(row=0,column=1,rowspan=2,sticky="ns",padx=(4,0));self._controls.grid_propagate(False)
  self._menu_button=self._control(self._controls,"M",self._toggle_earth_menu,BLUE);self._menu_button.pack(fill=tk.X,padx=5,pady=(7,2));self._menu_button.pack_forget()
  self._follow_button=self._control(self._controls,"F",self._toggle_follow,GREEN);self._follow_button.pack(fill=tk.X,padx=5,pady=(7,2));self.set_follow_enabled(self._follow_enabled)
  self._chase_button=self._control(self._controls,"C̸",self._toggle_chase,TEXT);self._chase_button.pack(fill=tk.X,padx=5,pady=(0,4));self._update_chase_button()
  pan=tk.Frame(self._controls,bg=PANEL);pan.pack(pady=2)
  for row,col,text,up,right in ((0,1,"▲",1,0),(1,0,"◀",0,-1),(1,2,"▶",0,1),(2,1,"▼",-1,0)):
   tk.Button(pan,text=text,command=lambda u=up,r=right:self._pan(u,r),bg="#101820",fg=TEXT,activebackground=BLUE,activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",9,"bold"),width=1,height=1,padx=2,pady=1).grid(row=row,column=col,padx=1,pady=1)
  for text,cmd,accent in (("+",lambda:self._change_zoom(1),BLUE),("−",lambda:self._change_zoom(-1),BLUE),("↗",lambda:self._change_pitch(5),PURPLE),("↘",lambda:self._change_pitch(-5),PURPLE),("↶",lambda:self._rotate_earth(-15),RED),("↷",lambda:self._rotate_earth(15),RED),("N",self._north_up,TEXT),("◎",self._recenter,GREEN)):
   self._control(self._controls,text,cmd,accent).pack(fill=tk.X,padx=5,pady=2)
  tk.Label(self._controls,text="FOLLOW\nCHASE\nZOOM\nTILT\nROTATE\nNORTH\nCENTER",bg=PANEL,fg=MUTED,font=("Sans",6),justify=tk.CENTER).pack(side=tk.BOTTOM,pady=5)
  self._earth_compact=tk.Frame(self._body,bg=PANEL,highlightthickness=1,highlightbackground=BORDER);self._earth_instruction_var=tk.StringVar(value="No active route");self._earth_maneuver_distance_var=tk.StringVar(value="");self._earth_route_remaining_var=tk.StringVar(value="");self._earth_speed_var=tk.StringVar(value="-- mph");self._earth_track_var=tk.StringVar(value="---°");self._earth_position_var=tk.StringVar(value="GPS --")
  tk.Label(self._earth_compact,text="➜",bg=PANEL,fg=GREEN,font=("Sans",16,"bold"),padx=8).pack(side=tk.LEFT);tk.Label(self._earth_compact,textvariable=self._earth_instruction_var,bg=PANEL,fg=TEXT,font=("Sans",10,"bold"),anchor="w").pack(side=tk.LEFT,fill=tk.X,expand=True,pady=4);tk.Label(self._earth_compact,textvariable=self._earth_maneuver_distance_var,bg=PANEL,fg=GREEN,font=("Sans",9,"bold"),padx=7).pack(side=tk.RIGHT);tk.Label(self._earth_compact,textvariable=self._earth_speed_var,bg=PANEL,fg=GREEN,font=("Sans",10,"bold"),padx=7).pack(side=tk.RIGHT);tk.Label(self._earth_compact,textvariable=self._earth_track_var,bg=PANEL,fg=TEXT,font=("Sans",8,"bold"),padx=6).pack(side=tk.RIGHT);tk.Label(self._earth_compact,textvariable=self._earth_route_remaining_var,bg=PANEL,fg=MUTED,font=("Sans",7),padx=6).pack(side=tk.RIGHT)
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
 def _set_earth_layout(self,enabled:bool)->None:
  if enabled:
   self._bar.grid_remove();self._menu_button.pack(fill=tk.X,padx=5,pady=(7,2),before=self._follow_button);self._earth_compact.grid(row=1,column=0,sticky="ew",pady=(3,0));self._controls.grid_configure(rowspan=2);self._update_menu_button()
  else:
   self._earth_compact.grid_remove();self._menu_button.pack_forget();self._bar.grid();self._controls.grid_configure(rowspan=2)
 def _embed_earth(self)->None:
  self._set_earth_layout(True);self.update_idletasks();position,size=self._earth_geometry()
  if not self._earth_launcher.is_running():self._earth_launcher.configure_app_window(position=position,size=size);self._earth_launcher.launch(self._display())
  self.update_idletasks();self._earth_embedder.embed(0,self.map_host_window_id,size[0],size[1],window_class=GoogleEarthLauncher.WINDOW_CLASS)
  self._earth_last_sent_position=None;self._earth_watch_count=0;self._earth_tracking_primed=False;self._earth_follow_enabled=True;self._earth_chase.set_enabled(False);self._earth_geolocation.install();self._earth_vehicle.install();self._earth_visible=True;self._earth_button.configure(text="▣  MAP",bg=GREEN,fg=BG);self._earth_map_overlay.show();self._update_follow_button();self._update_chase_button();self._start_earth_hud()
 def _detach_earth(self)->None:
  if self._earth_embedder.window_id is not None:
   try:self._earth_embedder.detach(int(self.winfo_toplevel().winfo_id()))
   except (OSError,RuntimeError):pass
  self._earth_embedder.clear()
 def _leave_earth(self)->None:
  self._earth_chase.set_enabled(False);self._stop_earth_hud();self._earth_map_overlay.hide();self._earth_vehicle.remove();self._detach_earth();self._set_earth_layout(False);self._earth_visible=False;self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="white");self._update_follow_button();self._update_chase_button();self._shortcut_status.set("MapLibre")
 def _toggle_earth(self):
  try:
   if self._earth_visible:self._leave_earth();return
   self._prepare_first_earth_launch();self._embed_earth()
  except Exception as exc:
   self._earth_visible=False;self._earth_chase.set_enabled(False);self._stop_earth_hud();self._earth_map_overlay.hide();self._earth_vehicle.remove();self._detach_earth();self._set_earth_layout(False)
   if self._earth_launcher.is_running():
    try:self._earth_launcher.stop(self._display())
    except Exception:pass
   self._earth_initialized=False;self._earth_button.configure(text="◉  EARTH",bg=BLUE,fg="white");self._update_follow_button();self._update_chase_button();self._shortcut_status.set(f"Earth unavailable: {exc}")
 def _toggle_earth_menu(self):
  if not self._earth_visible:return
  if self._earth_embedder.send_key("ctrl+shift+b"):
   self._earth_menu_visible=not self._earth_menu_visible;self._update_menu_button();self._shortcut_status.set("Earth menu shown" if self._earth_menu_visible else "Earth menu hidden")
  else:self._shortcut_status.set("Earth menu control unavailable")
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
  if self._earth_follow_enabled and self._earth_chase.enabled:self._earth_chase.update(track_rad=track,speed_m_s=speed)
  self._earth_vehicle.install();self._earth_vehicle.update_attitude(heading_rad=self._camera_runtime.latest_heading_rad,pitch_rad=self._camera_runtime.latest_pitch_rad,roll_rad=self._camera_runtime.latest_roll_rad)
  self._update_earth_guidance();self._earth_hud_after=self.after(100,self._update_earth_hud)
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
  self._earth_maneuver_distance_var.set(self._format_distance(self._camera_runtime.latest_distance_to_maneuver_m));remaining=self._camera_runtime.latest_distance_remaining_m;self._earth_route_remaining_var.set("" if remaining is None else f"{remaining*_M_TO_MI:.1f} mi")
 @staticmethod
 def _format_distance(distance_m:float|None)->str:
  if distance_m is None:return ""
  if distance_m<304.8:return f"{max(0.0,distance_m)*_M_TO_FT:.0f} ft"
  return f"{max(0.0,distance_m)*_M_TO_MI:.1f} mi"
 @staticmethod
 def _cardinal(track_rad:float)->str:
  names=("N","NE","E","SE","S","SW","W","NW");return names[int((math.degrees(track_rad)%360.0+22.5)//45.0)%8]
 def _on_map_host_resize(self,event):
  if self._earth_visible:self._earth_embedder.resize(max(1,event.width),max(1,event.height));self._earth_map_overlay.reposition()
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
   else:
    self._earth_chase.set_enabled(False);self._update_chase_button();self._shortcut_status.set("Earth follow off")
   self._update_follow_button();return
  self.set_follow_enabled(not self._follow_enabled);self._request_handler.request_follow(self._follow_enabled)
 def _toggle_chase(self):
  if not self._earth_visible:self._shortcut_status.set("Earth chase only");return
  enable=not self._earth_chase.enabled
  if enable:
   self._earth_follow_enabled=True;self._earth_tracking_primed=False;self._earth_last_sent_position=None
   self._earth_geolocation.install();self._send_earth_position(force=True);self._earth_input.activate_location_tracking()
  ok=self._earth_chase.set_enabled(enable)
  if enable:self.after(250,self._refresh_earth_tracking_watch)
  self._update_follow_button();self._update_chase_button();self._shortcut_status.set("Earth chase on" if ok and enable else "Earth chase off" if ok else "Earth chase unavailable")
 def _pan(self,up:float,right:float):
  if self._earth_visible:
   self._earth_chase.set_enabled(False);self._update_chase_button();self._earth_follow_enabled=False;self._update_follow_button()
   ok=self._earth_input.pan(up=up,right=right);self._shortcut_status.set("Earth pan" if ok else "Earth pan unavailable");return
  self.set_follow_enabled(False);self._map_host.update_idletasks();self._request_handler.request_pan_screen(right_px=right*max(48,self._map_host.winfo_width()*.25),up_px=up*max(48,self._map_host.winfo_height()*.25))
 def _change_zoom(self,d):
  if self._earth_visible:
   ok=self._earth_input.zoom_in() if d>0 else self._earth_input.zoom_out();self._shortcut_status.set("Earth zoom" if ok else "Earth zoom unavailable");return
  self._zoom_level=max(1,min(22,self._zoom_level+d));self.set_follow_enabled(False);self._request_handler.request_zoom(self._zoom_level)
 def _change_pitch(self,delta_deg:float):
  if self._earth_visible:
   ok=self._earth_input.tilt(delta_deg);self._shortcut_status.set("Earth tilt" if ok else "Earth tilt unavailable");return
  pitch_deg=max(0,min(60,math.degrees(self._pitch_rad)+delta_deg));self._pitch_rad=math.radians(pitch_deg);self.set_follow_enabled(False);self._request_handler.request_pitch(self._pitch_rad)
 def _rotate_earth(self,delta_deg:float):
  if not self._earth_visible:self._shortcut_status.set("Earth rotation only");return
  self._earth_chase.set_enabled(False);self._update_chase_button();self._earth_follow_enabled=False;self._update_follow_button();ok=self._earth_input.rotate(delta_deg);self._shortcut_status.set("Earth rotate" if ok else "Earth rotate unavailable")
 def _north_up(self):
  if self._earth_visible:
   self._earth_chase.set_enabled(False);self._update_chase_button();self._shortcut_status.set("Earth north up" if self._earth_input.north_up() else "Earth north-up unavailable");return
  self.set_follow_enabled(False);self._request_handler.request_bearing(0.0)
 def _recenter(self):
  if self._earth_visible:
   self._earth_follow_enabled=True;self._earth_tracking_primed=False;self._earth_last_sent_position=None;self._update_follow_button()
   self._earth_geolocation.install();self._send_earth_position(force=True);self._earth_input.activate_location_tracking();self.after(250,self._refresh_earth_tracking_watch);self._shortcut_status.set("Earth recenter requested")
   return
  self.set_follow_enabled(True);self._request_handler.request_recenter()
