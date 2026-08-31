# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Full navigation panel for the integrated ORC cockpit UI."""
from __future__ import annotations
import math
import tkinter as tk
from collections.abc import Callable
from apps.orcUi.map_camera_runtime import MapCameraRuntime
from ui.navigation import MapRequestHandlerIf

BG="#05090d"; PANEL="#0b1117"; BORDER="#25313b"; TEXT="#edf2f5"; MUTED="#89959e"; GREEN="#84ce1f"; BLUE="#168bd1"; RED="#f15a16"; PURPLE="#a25ce5"

class NavigationPanel(tk.Frame):
    def __init__(self,parent:tk.Misc,*,on_back:Callable[[],None]|None=None)->None:
        super().__init__(parent,bg=BG); del on_back
        self._zoom_level=16.5; self._pitch_rad=math.radians(45.0); self._follow_enabled=True; self._poi_focus:str|None=None
        self._camera_runtime=MapCameraRuntime(zoom_level=self._zoom_level,pitch_rad=self._pitch_rad,follow_enabled=True)
        self._request_handler=self._camera_runtime.request_handler; self._build(); self.bind("<Destroy>",self._on_destroy,add="+"); self._camera_runtime.start()
    @property
    def map_host_window_id(self)->int: self.update_idletasks(); return self._map_host.winfo_id()
    def set_map_request_handler(self,handler:MapRequestHandlerIf|None)->None:
        if handler is not None: self._request_handler=handler
    def set_follow_enabled(self,enabled:bool)->None:
        self._follow_enabled=enabled; self._follow_button.configure(text="F" if enabled else "F̸",fg=GREEN if enabled else TEXT)
    def _build(self)->None:
        self.grid_rowconfigure(1,weight=1); self.grid_columnconfigure(0,weight=1)
        bar=tk.Frame(self,bg=BG,height=38); bar.grid(row=0,column=0,sticky="ew",pady=(0,4)); bar.grid_propagate(False)
        shortcuts=tk.Frame(bar,bg=BG); shortcuts.pack(side=tk.LEFT,padx=2,pady=3)
        for text,accent,key in (("⌂ HOME",BLUE,"home"),("▣ WORK",PURPLE,"work"),("⛽ GAS",GREEN,"gas"),("♨ FOOD",RED,"food")):
            tk.Button(shortcuts,text=text,command=lambda s=key:self._destination_shortcut(s),bg=PANEL,fg=accent,activebackground="#101820",activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",8,"bold"),width=9,height=1,padx=3,pady=1).pack(side=tk.LEFT,padx=(0,4))
        self._shortcut_status=tk.StringVar(value="")
        tk.Label(bar,textvariable=self._shortcut_status,bg=BG,fg=MUTED,font=("Sans",7),anchor="e").pack(side=tk.RIGHT,padx=5)

        body=tk.Frame(self,bg=BG); body.grid(row=1,column=0,sticky="nsew"); body.grid_rowconfigure(0,weight=1); body.grid_columnconfigure(0,weight=1)
        self._map_host=tk.Frame(body,bg="#020406",highlightthickness=1,highlightbackground=BORDER); self._map_host.grid(row=0,column=0,sticky="nsew")
        controls=tk.Frame(body,bg=PANEL,width=62); controls.grid(row=0,column=1,sticky="ns",padx=(4,0)); controls.grid_propagate(False)
        self._follow_button=self._control(controls,"F",self._toggle_follow,GREEN); self._follow_button.pack(fill=tk.X,padx=5,pady=(7,5))
        pan=tk.Frame(controls,bg=PANEL); pan.pack(pady=2)
        for row,col,text,up,right in ((0,1,"▲",1,0),(1,0,"◀",0,-1),(1,2,"▶",0,1),(2,1,"▼",-1,0)):
            tk.Button(pan,text=text,command=lambda u=up,r=right:self._pan(u,r),bg="#101820",fg=TEXT,activebackground=BLUE,activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",9,"bold"),width=1,height=1,padx=2,pady=1).grid(row=row,column=col,padx=1,pady=1)
        for text,command,accent in (("+",lambda:self._change_zoom(1),BLUE),("−",lambda:self._change_zoom(-1),BLUE),("↗",lambda:self._change_pitch(5),PURPLE),("↘",lambda:self._change_pitch(-5),PURPLE),("N",self._north_up,TEXT),("◎",self._recenter,GREEN)):
            self._control(controls,text,command,accent).pack(fill=tk.X,padx=5,pady=2)
        tk.Label(controls,text="ZOOM\nTILT\nNORTH\nCENTER",bg=PANEL,fg=MUTED,font=("Sans",6),justify=tk.CENTER).pack(side=tk.BOTTOM,pady=5)
    def _control(self,parent,text,command,fg):
        return tk.Button(parent,text=text,command=command,bg=PANEL,fg=fg,activebackground="#101820",activeforeground=TEXT,relief=tk.FLAT,highlightthickness=1,highlightbackground=BORDER,font=("Sans",11,"bold"),height=1)
    def _on_destroy(self,event:tk.Event)->None:
        if event.widget is self: self._camera_runtime.close()
    def _destination_shortcut(self,shortcut:str)->None:
        if shortcut=="gas":
            self._poi_focus=None if self._poi_focus=="fuel" else "fuel"; self._request_handler.request_poi_focus(self._poi_focus)
            self._shortcut_status.set("Fuel stations highlighted" if self._poi_focus else "Fuel focus off"); return
        self._request_handler.request_poi_focus(None); self._poi_focus=None
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
