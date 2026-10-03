# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Persistent shell-level presentation for asynchronous weather alerts."""
from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from ui.theme import ThemeBundle
from ui.weather import WeatherAlertUiEvent

def weather_alert_expiration_text(alert: WeatherAlertUiEvent, now: datetime) -> str:
    if alert.expires_at is None:
        return ""
    seconds=(alert.expires_at-now).total_seconds()
    if seconds <= 0:
        return "EXPIRED"
    minutes=max(1,int((seconds+59)//60))
    if minutes < 60:
        return f"Expires in {minutes} min"
    hours,remaining=divmod(minutes,60)
    return f"Expires in {hours}h {remaining}m" if remaining else f"Expires in {hours}h"

class WeatherAlertBanner(tk.Frame):
    def __init__(self,parent:tk.Misc,*,theme:ThemeBundle,on_details:Callable[[],None],on_dismiss:Callable[[],None])->None:
        self._theme=theme;self._alert=None;self._on_details=on_details;self._on_dismiss=on_dismiss
        super().__init__(parent,bd=0,highlightthickness=1);self.grid_columnconfigure(1,weight=1)
        self._severity=tk.Label(self,font=("Sans",10,"bold"),padx=8,pady=6);self._severity.grid(row=0,column=0,rowspan=2,sticky="nsw")
        self._event=tk.Label(self,anchor="w",font=("Sans",12,"bold"),padx=8);self._event.grid(row=0,column=1,sticky="ew",pady=(4,0))
        self._headline=tk.Label(self,anchor="w",font=("Sans",9),padx=8);self._headline.grid(row=1,column=1,sticky="ew",pady=(0,4))
        self._expiration=tk.Label(self,anchor="e",font=("Sans",9,"bold"),padx=6);self._expiration.grid(row=0,column=2,rowspan=2,sticky="e")
        self._details=tk.Button(self,text="DETAILS",command=self._on_details,relief=tk.FLAT,bd=0,cursor="hand2",font=("Sans",9,"bold"));self._details.grid(row=0,column=3,rowspan=2,padx=(4,2),pady=5)
        self._dismiss=tk.Button(self,text="✕",command=self._on_dismiss,relief=tk.FLAT,bd=0,cursor="hand2",width=3,font=("Sans",11,"bold"));self._dismiss.grid(row=0,column=4,rowspan=2,padx=(2,6),pady=5)
        self.set_theme_bundle(theme)
    @property
    def alert(self):return self._alert
    def set_alert(self,alert):
        self._alert=alert;self._severity.configure(text=alert.severity.upper());self._event.configure(text=alert.event.upper());self._headline.configure(text=alert.headline);self.update_expiration(datetime.now().astimezone());self.set_theme_bundle(self._theme)
    def update_expiration(self,now:datetime)->None:
        if self._alert is not None:self._expiration.configure(text=weather_alert_expiration_text(self._alert,now))
    def set_theme_bundle(self,theme):
        self._theme=theme;ui=theme.ui;accent=self._severity_color();self.configure(bg=ui.surface_alt,highlightbackground=accent)
        self._severity.configure(bg=accent,fg=ui.control_text);self._event.configure(bg=ui.surface_alt,fg=ui.text);self._headline.configure(bg=ui.surface_alt,fg=ui.text_muted);self._expiration.configure(bg=ui.surface_alt,fg=ui.text_muted)
        for button in (self._details,self._dismiss):button.configure(bg=ui.control_background,fg=ui.control_text,activebackground=ui.control_active,activeforeground=ui.text)
    def _severity_color(self):
        severity="" if self._alert is None else self._alert.severity.lower();ui=self._theme.ui
        if severity in {"extreme","severe"}:return ui.accent_danger
        if severity=="moderate":return ui.accent_primary
        return ui.accent_success
