# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Entry point for the integrated OpenRoadCode automotive UI."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tkinter as tk
from datetime import datetime

from apps.launchers.map_renderer_launcher import MapRendererLauncher
from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.context_rail import ContextRail
from apps.orcUi.home_map_panel import HomeMapPanel
from apps.orcUi.media_panel import MediaPanel
from apps.orcUi.navigation_panel import NavigationPanel
from apps.orcUi.navigation_presenter import AttitudePresentationState, NavigationPresenter, PositionPresentationState
from apps.orcUi.offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import ThemeMode, apply_tk_theme, install_map_style, toggle, toggle_label
from apps.orcUi.radio_panel import RadioPanel
from apps.orcUi.spotify_local_player import SpotifyLocalPlayer
from apps.orcUi.spotify_now_playing import SpotifyNowPlaying
from apps.orcUi.spotify_state_service import SpotifyStateService
from apps.orcUi.vehicle_panel import VehiclePanel
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from frontends.x11 import X11WindowEmbedder
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.contracts.navigation import ATTITUDE_STATE_TOPIC, POSITION_STATE_TOPIC, decode_attitude_state, decode_position_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT

BG="#05090d"; PANEL="#0b1117"; BORDER="#25313b"; TEXT="#edf2f5"; MUTED="#89959e"; GREEN="#84ce1f"; BLUE="#168bd1"; RED="#f15a16"; PURPLE="#a25ce5"; YELLOW="#d6ad22"; TOP_BG="#020406"

class OrcUiApp:
    def __init__(self) -> None:
        self._root=tk.Tk(); self._root.title("OpenRoadCode"); self._root.geometry("1024x600"); self._root.minsize(1024,600); self._root.configure(bg=BG)
        self._theme_mode=ThemeMode.DARK; self._theme_button:tk.Button; self._power_button:tk.Button; self._power_dialog:tk.Toplevel|None=None
        self._active_nav="HOME"; self._nav_buttons:dict[str,tk.Button]={}; self._clock_label:tk.Label; self._content:tk.Frame
        self._context_rail=None; self._home_map_panel=None; self._navigation_panel=None; self._radio_panel=None; self._radio_embedder=X11WindowEmbedder(); self._vehicle_panel=None; self._offroad_panel=None; self._media_panel=None
        self._map_renderer=MapRendererLauncher(); self._spotify_service=SpotifyStateService(); self._spotify_local_player=SpotifyLocalPlayer(spotify_service=self._spotify_service); self._vehicle_state=VehiclePresentationState(); self._position_state=PositionPresentationState(); self._attitude_state=AttitudePresentationState(); self._volume=20; self._volume_label:tk.Label; self._closing=False
        self._dispatcher=MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),error_handler=self._on_bus_error)
        self._dispatcher.register(VEHICLE_STATE_TOPIC,decode_vehicle_state,self._on_vehicle_message); self._dispatcher.register(POSITION_STATE_TOPIC,decode_position_state,self._on_position_message); self._dispatcher.register(ATTITUDE_STATE_TOPIC,decode_attitude_state,self._on_attitude_message)
        install_map_style(self._theme_mode); self._build_shell(); self._spotify_service.start(); self._show_home(); self._update_clock()
    def run(self):
        self._root.protocol("WM_DELETE_WINDOW",self._on_close); old=signal.getsignal(signal.SIGINT); signal.signal(signal.SIGINT,self._on_sigint); self._dispatcher.start()
        try:self._root.mainloop()
        except KeyboardInterrupt:self._shutdown()
        finally:signal.signal(signal.SIGINT,old); self._shutdown()
    def _on_sigint(self,_signum,_frame): self._root.after_idle(self._shutdown)
    def _shutdown(self):
        if self._closing:return
        self._closing=True; self._map_renderer.stop(); self._dispatcher.close(); self._spotify_local_player.close(); self._spotify_service.close()
        if self._media_panel is not None:self._media_panel.close()
        try:self._root.destroy()
        except tk.TclError:pass
    def _build_shell(self):
        self._root.grid_rowconfigure(1,weight=1); self._root.grid_columnconfigure(1,weight=1); self._build_top_bar(); self._build_side_nav(); self._content=tk.Frame(self._root,bg=BG); self._content.grid(row=1,column=1,sticky="nsew",padx=(6,8),pady=6); self._build_bottom_bar(); self._build_footer()
    def _build_top_bar(self):
        bar=tk.Frame(self._root,bg=TOP_BG,height=50); bar.grid(row=0,column=0,columnspan=2,sticky="ew"); bar.grid_propagate(False); bar.grid_columnconfigure(1,weight=1)
        brand=tk.Frame(bar,bg=TOP_BG); brand.grid(row=0,column=0,sticky="w",padx=(10,8)); self._build_logo_mark(brand)
        for letter,color in (("O",BLUE),("R",RED),("C",GREEN)):tk.Label(brand,text=letter,fg=color,bg=TOP_BG,font=("Sans",21,"bold"),padx=0,pady=0,bd=0).pack(side=tk.LEFT,padx=0)
        tk.Label(brand,text="ui",fg="#c5ccd2",bg=TOP_BG,font=("Monospace",12),padx=0).pack(side=tk.LEFT,padx=(3,0),pady=(5,0)); self._clock_label=tk.Label(bar,fg=TEXT,bg=TOP_BG,font=("Sans",17,"bold")); self._clock_label.grid(row=0,column=1)
        status=tk.Frame(bar,bg=TOP_BG); status.grid(row=0,column=2,padx=(8,14),sticky="e"); tk.Label(status,text="☁  --°F",fg=TEXT,bg=TOP_BG,font=("Sans",11,"bold")).pack(side=tk.LEFT,padx=(0,10)); tk.Label(status,text="GPS  ▮▮▮   WiFi   BT   🚗",fg="#b8c0c6",bg=TOP_BG,font=("Sans",11)).pack(side=tk.LEFT,padx=(0,10)); self._power_button=tk.Button(status,text="⏻",command=self._show_power_dialog,bg="#101820",fg=TEXT,relief=tk.FLAT,bd=0,font=("Sans",16,"bold"),padx=10,pady=2); self._power_button.pack(side=tk.LEFT)
    @staticmethod
    def _build_logo_mark(parent):
        logo=tk.Canvas(parent,width=32,height=30,bg=TOP_BG,highlightthickness=0,bd=0); logo.pack(side=tk.LEFT,padx=(0,4)); logo.create_line(16,3,3,26,fill=BLUE,width=4); logo.create_line(3,26,29,26,fill=RED,width=4); logo.create_line(29,26,16,3,fill=GREEN,width=4); logo.create_line(16,9,16,21,fill="#d7dde2",width=2,dash=(3,3))
    def _build_side_nav(self):
        nav=tk.Frame(self._root,bg="#070c11",width=112); nav.grid(row=1,column=0,sticky="ns",padx=(8,0),pady=6); nav.grid_propagate(False)
        for item in ["HOME","NAVIGATION","RADIO","MEDIA","VEHICLE","LIGHTING","CONTROLS","SETTINGS"]:
            b=tk.Button(nav,text=item,command=lambda name=item:self._select_nav(name),bg="#070c11",fg="#c7cdd2",relief=tk.FLAT,bd=0,font=("Sans",9),height=3); b.pack(fill=tk.X,padx=4,pady=2); self._nav_buttons[item]=b
        self._paint_nav()
    def _build_bottom_bar(self):
        bar=tk.Frame(self._root,bg=BG,height=55); bar.grid(row=2,column=0,columnspan=2,sticky="ew",padx=8,pady=(0,5)); bar.grid_propagate(False); bar.grid_columnconfigure(0,weight=2)
        for col in range(1,6):bar.grid_columnconfigure(col,weight=1)
        volume=tk.Frame(bar,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); volume.grid(row=0,column=0,sticky="nsew",padx=3); volume.grid_columnconfigure(1,weight=1); tk.Button(volume,text="−",command=lambda:self._change_volume(-5),bg=PANEL,fg=TEXT,relief=tk.FLAT,bd=0,font=("Sans",16,"bold")).grid(row=0,column=0,sticky="ns",padx=4); self._volume_label=tk.Label(volume,text="🔊 20%",bg=PANEL,fg=TEXT,font=("Sans",10,"bold")); self._volume_label.grid(row=0,column=1); tk.Button(volume,text="+",command=lambda:self._change_volume(5),bg=PANEL,fg=TEXT,relief=tk.FLAT,bd=0,font=("Sans",15,"bold"),padx=4).grid(row=0,column=2,sticky="ns");
        for col,text in enumerate(["🎙  Push to Talk","▣  Front Cam","▣  SCREEN\nAuto","☀  BRIGHTNESS\n70%"],start=1):tk.Button(bar,text=text,bg=PANEL,fg=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",9)).grid(row=0,column=col,sticky="nsew",padx=3)
        self._theme_button=tk.Button(bar,text=toggle_label(self._theme_mode),command=self._toggle_theme,bg=PANEL,fg=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",9,"bold")); self._theme_button.grid(row=0,column=5,sticky="nsew",padx=3)
    def _change_volume(self,delta): self._volume=max(0,min(100,self._volume+delta)); self._volume_label.configure(text=f"{'🔇' if self._volume==0 else '🔊'} {self._volume}%")
    def _show_power_dialog(self):
        if self._power_dialog is not None and self._power_dialog.winfo_exists():self._power_dialog.lift(); return
        d=tk.Toplevel(self._root); self._power_dialog=d; d.title("OpenRoadCode Power"); d.transient(self._root); d.resizable(False,False); d.configure(bg=PANEL); d.protocol("WM_DELETE_WINDOW",self._close_power_dialog); f=tk.Frame(d,bg=PANEL,padx=18,pady=16); f.pack(fill=tk.BOTH,expand=True); tk.Label(f,text="POWER",fg=TEXT,bg=PANEL,font=("Sans",16,"bold")).pack(pady=(0,4)); tk.Label(f,text="System actions are intentionally two taps away.",fg=MUTED,bg=PANEL,font=("Sans",9)).pack(pady=(0,14))
        for text,cmd in (("EXIT UI",self._on_close),("RESTART UI",self._restart_ui),("SHUT DOWN SYSTEM",self._show_shutdown_confirmation),("CANCEL",self._close_power_dialog)):tk.Button(f,text=text,command=cmd,bg="#101820",fg=TEXT,relief=tk.FLAT,width=24,pady=8,font=("Sans",10,"bold")).pack(fill=tk.X,pady=3)
        self._center_power_dialog(d)
    def _show_shutdown_confirmation(self): self._shutdown_system()
    def _reopen_power_dialog(self): self._close_power_dialog(); self._show_power_dialog()
    def _close_power_dialog(self):
        d=self._power_dialog; self._power_dialog=None
        if d is not None and d.winfo_exists():d.destroy()
    def _restart_ui(self): self._map_renderer.stop(); self._dispatcher.close(); self._spotify_local_player.close(); self._spotify_service.close(); os.execv(sys.executable,[sys.executable,"-m","apps.orcUi"])
    def _shutdown_system(self):
        command=["systemctl","poweroff"] if shutil.which("systemctl") else (["loginctl","poweroff"] if shutil.which("loginctl") else None)
        if command is None:return
        self._map_renderer.stop(); self._dispatcher.close(); self._spotify_local_player.close(); self._spotify_service.close(); subprocess.Popen(command); self._shutdown()
    def _center_power_dialog(self,d):
        d.update_idletasks(); w=d.winfo_reqwidth(); h=d.winfo_reqheight(); x=self._root.winfo_rootx()+max(0,(self._root.winfo_width()-w)//2); y=self._root.winfo_rooty()+max(0,(self._root.winfo_height()-h)//2); d.geometry(f"{w}x{h}+{x}+{y}")
    def _toggle_theme(self):
        self._theme_mode=toggle(self._theme_mode); install_map_style(self._theme_mode); sync_sdrpp_theme("Light" if self._theme_mode is ThemeMode.LIGHT else "Dark"); apply_tk_theme(self._root,self._theme_mode); self._theme_button.configure(text=toggle_label(self._theme_mode)); self._paint_nav()
        if self._media_panel is not None and self._media_panel.winfo_exists():self._media_panel.set_theme_mode(self._theme_mode)
        self._reload_active_map()
    def _reload_active_map(self):
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():pid=self._home_map_panel.map_host_window_id
        elif self._navigation_panel is not None and self._navigation_panel.winfo_exists():pid=self._navigation_panel.map_host_window_id
        else:return
        self._map_renderer.stop(); self._root.after(100,lambda:self._start_map_renderer(pid))
    def _build_footer(self):
        f=tk.Frame(self._root,bg=TOP_BG,height=25); f.grid(row=3,column=0,columnspan=2,sticky="ew"); f.grid_propagate(False); f.grid_columnconfigure(1,weight=1); tk.Label(f,text="OpenRoadCode",fg="#aab2b8",bg=TOP_BG,font=("Sans",8)).grid(row=0,column=0,padx=10); tk.Label(f,text="Services: --   |   ZMQ: --",fg=MUTED,bg=TOP_BG,font=("Sans",8)).grid(row=0,column=1); tk.Label(f,text="orcUi prototype",fg=MUTED,bg=TOP_BG,font=("Sans",8)).grid(row=0,column=2,padx=10)
    def _select_nav(self,name):
        self._active_nav=name; self._paint_nav(); {"HOME":self._show_home,"NAVIGATION":self._show_navigation_panel,"RADIO":self._show_radio_panel,"MEDIA":self._show_media_panel,"VEHICLE":self._show_vehicle_panel}.get(name,lambda:self._show_placeholder(name))()
    def _paint_nav(self):
        for name,b in self._nav_buttons.items(): b.configure(fg=GREEN if name==self._active_nav else "#c7cdd2",bg="#101820" if name==self._active_nav else "#070c11")
    def _clear_content(self):
        self._map_renderer.stop()
        if self._radio_panel is not None and self._radio_panel.winfo_exists():self._radio_panel.detach_sdrpp(self._root.winfo_id())
        if self._media_panel is not None and self._media_panel.winfo_exists():self._media_panel.close()
        self._context_rail=self._home_map_panel=self._navigation_panel=self._radio_panel=self._vehicle_panel=self._offroad_panel=self._media_panel=None
        for child in self._content.winfo_children():child.destroy()
    def _show_home(self):
        self._clear_content(); self._active_nav="HOME"; self._paint_nav(); self._content.grid_columnconfigure(0,weight=1); self._content.grid_columnconfigure(1,weight=0,minsize=ContextRail.WIDTH); self._content.grid_rowconfigure(0,weight=3); self._content.grid_rowconfigure(1,weight=2); self._home_map_panel=HomeMapPanel(self._content); self._home_map_panel.grid(row=0,column=0,sticky="nsew",padx=(0,5),pady=(0,5)); self._context_rail=ContextRail(self._content,on_expand=self._show_context_full_panel); self._context_rail.update_vehicle_state(self._vehicle_state); self._context_rail.update_position_state(self._position_state); self._context_rail.grid(row=0,column=1,rowspan=2,sticky="nsew",padx=(5,0)); lower=tk.Frame(self._content,bg=BG); lower.grid(row=1,column=0,sticky="nsew",padx=(0,5),pady=(5,0)); lower.grid_columnconfigure(0,weight=4); lower.grid_columnconfigure(1,weight=1); lower.grid_rowconfigure(0,weight=1); radio=self._panel(lower,"RADIO",PURPLE); radio.grid(row=0,column=0,sticky="nsew",padx=(0,5)); self._summary(radio,"101.1 FM","Radio service"); media=self._panel(lower,"MEDIA",BLUE); media.grid(row=0,column=1,sticky="nsew",padx=(5,0)); SpotifyNowPlaying(media,service=self._spotify_service,on_open=self._show_spotify_from_home).pack(fill=tk.BOTH,expand=True)
        self._root.update_idletasks(); self._root.after(100,lambda:self._start_map_renderer(self._home_map_panel.map_host_window_id))
    def _show_spotify_from_home(self):
        self._show_media_panel()
        if self._media_panel is not None:self._media_panel.show_spotify()
    def _show_navigation_panel(self):
        self._clear_content(); self._active_nav="NAVIGATION"; self._paint_nav(); self._navigation_panel=NavigationPanel(self._content,on_back=self._show_home); self._navigation_panel.pack(fill=tk.BOTH,expand=True); self._root.update_idletasks(); self._root.after(100,lambda:self._start_map_renderer(self._navigation_panel.map_host_window_id))
    def _start_map_renderer(self,parent_window_id):
        try:self._map_renderer.launch(display=os.environ.get("DISPLAY",":1"),parent_window_id=parent_window_id)
        except (OSError,RuntimeError) as e:print(f"WARNING: map renderer: {type(e).__name__}: {e}")
    def _show_radio_panel(self): self._clear_content(); self._active_nav="RADIO"; self._paint_nav(); self._radio_panel=RadioPanel(self._content,embedder=self._radio_embedder); self._radio_panel.pack(fill=tk.BOTH,expand=True); self._root.update_idletasks(); self._root.after(100,self._attach_existing_sdrpp)
    def _attach_existing_sdrpp(self):
        p=self._radio_panel
        if p is None or not p.winfo_exists():return
        try:p.attach_sdrpp()
        except (OSError,RuntimeError,subprocess.SubprocessError) as e:print(f"WARNING: SDR++ embed: {type(e).__name__}: {e}")
    def _show_media_panel(self): self._clear_content(); self._active_nav="MEDIA"; self._paint_nav(); self._media_panel=MediaPanel(self._content,on_back=self._show_home,status_callback=lambda message:print(f"[Media] {message}"),theme_mode=self._theme_mode,spotify_service=self._spotify_service,spotify_local_player=self._spotify_local_player); self._media_panel.pack(fill=tk.BOTH,expand=True)
    def _show_vehicle_panel(self): self._clear_content(); self._active_nav="VEHICLE"; self._paint_nav(); self._vehicle_panel=VehiclePanel(self._content,on_back=self._show_home,state=self._vehicle_state); self._vehicle_panel.pack(fill=tk.BOTH,expand=True)
    def _show_offroad_panel(self): self._clear_content(); self._offroad_panel=OffRoadPanel(self._content,on_back=self._show_home,position=self._position_state,attitude=self._attitude_state); self._offroad_panel.pack(fill=tk.BOTH,expand=True)
    def _on_vehicle_message(self,m):
        s=VehiclePresenter.present(m.data)
        if not self._closing:self._root.after(0,self._apply_vehicle_state,s)
    def _apply_vehicle_state(self,s):
        if self._closing:return
        self._vehicle_state=s
        if self._context_rail is not None and self._context_rail.winfo_exists():self._context_rail.update_vehicle_state(s)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():self._vehicle_panel.update_state(s)
    def _on_position_message(self,m):
        s=NavigationPresenter.present_position(m.data)
        if not self._closing:self._root.after(0,self._apply_position_state,s)
    def _apply_position_state(self,s): self._position_state=s
    def _on_attitude_message(self,m): self._attitude_state=NavigationPresenter.present_attitude(m.data)
    @staticmethod
    def _on_bus_error(topic,error):print(f"WARNING: {topic}: {type(error).__name__}: {error}")
    def _on_close(self):self._shutdown()
    def _show_context_full_panel(self,name):
        if name=="VEHICLE":return self._show_vehicle_panel()
        if name=="OFF-ROAD":return self._show_offroad_panel()
        self._show_placeholder(name)
    @staticmethod
    def _panel(parent,title,accent): f=tk.Frame(parent,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); tk.Label(f,text=title,fg=accent,bg=PANEL,font=("Sans",10,"bold")).pack(anchor="nw",padx=14,pady=(11,4)); return f
    @staticmethod
    def _summary(parent,primary,secondary): tk.Label(parent,text=primary,fg=TEXT,bg=PANEL,font=("Sans",14,"bold")).pack(anchor="w",padx=16,pady=(12,2)); tk.Label(parent,text=secondary,fg=MUTED,bg=PANEL,font=("Sans",9)).pack(anchor="w",padx=16)
    def _show_placeholder(self,name): self._clear_content(); p=self._panel(self._content,name,GREEN); p.pack(fill=tk.BOTH,expand=True); tk.Label(p,text=f"{name}\nCOMING NEXT",fg=TEXT,bg=PANEL,font=("Sans",24,"bold")).place(relx=.5,rely=.5,anchor="center")
    def _update_clock(self):
        if self._closing:return
        self._clock_label.configure(text=datetime.now().strftime("%I:%M %p     %a, %b %d").lstrip("0")); self._root.after(1000,self._update_clock)

def main():OrcUiApp().run()
if __name__=="__main__":main()
