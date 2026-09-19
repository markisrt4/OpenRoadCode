# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Vehicle-friendly native Tk weather dashboard for orcUi."""
from __future__ import annotations
from collections.abc import Callable
from datetime import datetime
import tkinter as tk
from common.units import UnitSystem,kelvin_to_celsius,kelvin_to_fahrenheit,meters_per_second_to_kilometers_per_hour,meters_per_second_to_miles_per_hour,pascals_to_kilopascals
from ui.theme import ThemeBundle
from ui.weather import WeatherRequestHandlerIf,WeatherUiIf,WeatherUiState

class OrcWeatherPanel(tk.Frame,WeatherUiIf):
    def __init__(self,parent:tk.Misc,*,theme_bundle:Callable[[],ThemeBundle],unit_system:Callable[[],UnitSystem]=lambda:UnitSystem.IMPERIAL,on_weather_radio:Callable[[],None]|None=None)->None:
        self._theme_bundle=theme_bundle;self._unit_system=unit_system;self._on_weather_radio=on_weather_radio;self._handler=None;self._state=None
        ui=theme_bundle().ui;super().__init__(parent,bg=ui.background)
        self._header=tk.Frame(self,bg=ui.background);self._header.pack(fill=tk.X,padx=24,pady=(14,6))
        self._location=tk.Label(self._header,text="Weather",anchor="w",font=("Sans",20,"bold"));self._location.pack(side=tk.LEFT)
        self._provider=tk.Label(self._header,text="",anchor="e",font=("Sans",9));self._provider.pack(side=tk.RIGHT,padx=(12,0))
        self._refresh=tk.Button(self._header,text="REFRESH",command=self._request_refresh,padx=12,pady=5);self._refresh.pack(side=tk.RIGHT)
        self._weather_radio=tk.Button(self._header,text="NOAA RADIO",command=self._request_weather_radio,padx=12,pady=5);self._weather_radio.pack(side=tk.RIGHT,padx=(0,8))
        self._current_card=tk.Frame(self,bd=0,highlightthickness=1);self._current_card.pack(fill=tk.X,padx=24,pady=6)
        self._temperature=tk.Label(self._current_card,text="--°",font=("Sans",50,"bold"),anchor="w");self._temperature.grid(row=0,column=0,rowspan=2,sticky="w",padx=(18,24),pady=10)
        self._condition=tk.Label(self._current_card,text="Weather unavailable",font=("Sans",20,"bold"),anchor="w");self._condition.grid(row=0,column=1,sticky="sw",pady=(12,1))
        self._details=tk.Label(self._current_card,text="",font=("Sans",11),anchor="w");self._details.grid(row=1,column=1,sticky="nw",pady=(1,12))
        self._current_card.columnconfigure(1,weight=1)
        self._metrics=tk.Frame(self._current_card);self._metrics.grid(row=0,column=2,rowspan=2,sticky="nsew",padx=(12,18),pady=10)
        self._metric_labels=[tk.Label(self._metrics,font=("Sans",10),anchor="w") for _ in range(3)]
        for i,w in enumerate(self._metric_labels):w.grid(row=i,column=0,sticky="w",pady=2)
        self._hourly_title=tk.Label(self,text="NEXT HOURS",font=("Sans",10,"bold"),anchor="w");self._hourly_title.pack(fill=tk.X,padx=26,pady=(8,3))
        self._hourly=tk.Frame(self);self._hourly.pack(fill=tk.X,padx=24)
        self._daily_title=tk.Label(self,text="6-DAY FORECAST",font=("Sans",10,"bold"),anchor="w");self._daily_title.pack(fill=tk.X,padx=26,pady=(10,3))
        self._daily=tk.Frame(self);self._daily.pack(fill=tk.X,padx=24,pady=(0,10))
        self.set_theme_bundle(theme_bundle())
    def set_weather_request_handler(self,handler):self._handler=handler
    def set_weather_state(self,state):self._state=state;self._render()
    def set_theme_bundle(self,theme):
        ui=theme.ui;self.configure(bg=ui.background);self._header.configure(bg=ui.background);self._location.configure(bg=ui.background,fg=ui.text);self._provider.configure(bg=ui.background,fg=ui.text_muted)
        for b in (self._refresh,self._weather_radio):b.configure(bg=ui.control_background,fg=ui.control_text,activebackground=ui.control_active,activeforeground=ui.text,relief=tk.FLAT,bd=0)
        self._current_card.configure(bg=ui.surface,highlightbackground=ui.border);self._metrics.configure(bg=ui.surface)
        for w in (self._temperature,self._condition,self._details,*self._metric_labels):w.configure(bg=ui.surface)
        self._temperature.configure(fg=ui.text);self._condition.configure(fg=ui.text);self._details.configure(fg=ui.text_muted)
        for w in self._metric_labels:w.configure(fg=ui.text_muted)
        for w in (self._hourly_title,self._daily_title):w.configure(bg=ui.background,fg=ui.text_muted)
        for f in (self._hourly,self._daily):f.configure(bg=ui.background)
        self._render_forecasts()
    def _request_refresh(self):
        if self._handler:self._handler.request_refresh()
    def _request_weather_radio(self):
        if self._on_weather_radio:self._on_weather_radio()
    def _render(self):
        s=self._state
        if s is None:
            self._location.configure(text="Weather");self._provider.configure(text="");self._temperature.configure(text="--°");self._condition.configure(text="Weather unavailable");self._details.configure(text="Waiting for location and forecast")
            for w in self._metric_labels:w.configure(text="")
            self._render_forecasts();return
        c=s.current;self._location.configure(text=s.location_name or "Current Location");self._provider.configure(text=self._provider_text(s));self._temperature.configure(text=self._temperature_text(c.temperature_k));self._condition.configure(text=c.condition_label or "Unknown")
        self._details.configure(text=f"Feels {self._temperature_text(c.apparent_temperature_k)}  •  Humidity {self._percent(c.relative_humidity)}  •  Wind {self._speed_text(c.wind_speed_m_s)}")
        self._metric_labels[0].configure(text=f"Gusts   {self._speed_text(c.wind_gust_m_s)}")
        self._metric_labels[1].configure(text=f"Pressure   {self._pressure_text(c.pressure_pa)}")
        self._metric_labels[2].configure(text=f"Wind dir   {self._direction_text(c.wind_direction_deg)}")
        self._render_forecasts()
    def _provider_text(self,s):
        label=s.provider_label or "Weather"
        if s.fetched_at is None:return label
        return f"{label}  •  Updated {datetime.fromtimestamp(s.fetched_at).strftime('%I:%M %p').lstrip('0')}"
    def _render_forecasts(self):
        for f in (self._hourly,self._daily):
            for child in f.winfo_children():child.destroy()
        if self._state is None:return
        for col,item in enumerate(self._state.hourly[:6]):
            pop="" if item.precipitation_probability is None else f"Rain {self._percent(item.precipitation_probability)}"
            self._forecast_cell(self._hourly,col,item.timestamp.strftime("%I %p").lstrip("0"),self._temperature_text(item.temperature_k),item.condition_label,pop)
        for col,item in enumerate(self._state.daily[:6]):
            temps=f"{self._temperature_text(item.temperature_high_k)} / {self._temperature_text(item.temperature_low_k)}";pop="" if item.precipitation_probability is None else f"Rain {self._percent(item.precipitation_probability)}"
            self._forecast_cell(self._daily,col,item.date.strftime("%a"),temps,item.condition_label,pop)
    def _forecast_cell(self,parent,column,heading,value,detail,footer=""):
        ui=self._theme_bundle().ui;cell=tk.Frame(parent,bg=ui.surface,highlightthickness=1,highlightbackground=ui.border);cell.grid(row=0,column=column,sticky="nsew",padx=(0 if column==0 else 3,3));parent.columnconfigure(column,weight=1,uniform="forecast")
        tk.Label(cell,text=heading,bg=ui.surface,fg=ui.text_muted,font=("Sans",9,"bold")).pack(pady=(6,1));tk.Label(cell,text=value,bg=ui.surface,fg=ui.text,font=("Sans",14,"bold")).pack();tk.Label(cell,text=detail,bg=ui.surface,fg=ui.text_muted,font=("Sans",8),wraplength=110).pack(padx=3,pady=(1,0));tk.Label(cell,text=footer,bg=ui.surface,fg=ui.text_muted,font=("Sans",8)).pack(pady=(0,6))
    def _temperature_text(self,v):
        if v is None:return "--°"
        return f"{kelvin_to_fahrenheit(v):.0f}°F" if self._unit_system() is UnitSystem.IMPERIAL else f"{kelvin_to_celsius(v):.0f}°C"
    def _speed_text(self,v):
        if v is None:return "--"
        return f"{meters_per_second_to_miles_per_hour(v):.0f} mph" if self._unit_system() is UnitSystem.IMPERIAL else f"{meters_per_second_to_kilometers_per_hour(v):.0f} km/h"
    def _pressure_text(self,v):
        if v is None:return "--"
        kpa=pascals_to_kilopascals(v)
        return f"{kpa*0.2952998751:.2f} inHg" if self._unit_system() is UnitSystem.IMPERIAL else f"{kpa:.1f} kPa"
    @staticmethod
    def _percent(v):return "--" if v is None else f"{v*100:.0f}%"
    @staticmethod
    def _direction_text(v):
        if v is None:return "--"
        names=("N","NE","E","SE","S","SW","W","NW")
        return f"{names[int((v+22.5)%360//45)]} {v:.0f}°"
