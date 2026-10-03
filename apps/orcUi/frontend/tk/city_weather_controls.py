# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact city forecast controls for the shared Navigation weather menu."""

import tkinter as tk

from .shell_metrics import FONT_CONTROL
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState
from frontends.common.weather_overlay_format import city_time_label


class CityWeatherControls:
    """Display a field selector, time window and independent city playback."""

    def __init__(self, parent, handler: WeatherOverlayRequestHandlerIf, state: CityWeatherOverlayState, ui):
        self._handler, self._state = handler, state
        self._ui = ui
        self._enabled = tk.BooleanVar(parent, value=state.enabled)
        self._kind = tk.StringVar(parent, value=state.kind)
        self._period = tk.StringVar(parent, value=state.period)
        self._hours = tk.DoubleVar(parent, value=state.hours)
        self._updating = False
        tk.Checkbutton(parent, text="City weather", variable=self._enabled,
                       command=lambda: handler.request_city_enabled(self._enabled.get()),
                       bg=ui.control_background, fg=ui.text, selectcolor=ui.background,
                       activebackground=ui.control_background, activeforeground=ui.text,
                       font=("Sans", FONT_CONTROL)).pack(anchor="w", pady=4)
        fields = self._row(parent)
        for value, text in (("temperature", "Temp"), ("wind", "Wind speed"), ("precipitation", "Precip total")):
            self._radio(fields, self._kind, value, text)
        periods = self._row(parent)
        for value, text in (("past", "Recent history"), ("future", "Forecast")):
            self._radio(periods, self._period, value, text)
        self._scale = tk.Scale(parent, from_=1, to=24, resolution=1, orient=tk.HORIZONTAL,
                               variable=self._hours, command=self._scrub, label="Hours", length=315,
                               bg=ui.control_background, fg=ui.text, troughcolor=ui.background,
                               highlightthickness=0, font=("Sans", FONT_CONTROL),
                               activebackground=ui.control_active)
        self._scale.pack(fill=tk.X, pady=3)
        self._time = self._label(parent, "")
        buttons = self._row(parent)
        self._play = tk.Button(buttons, text="Play", command=lambda: handler.request_city_playback(not self._state.playing),
                               bg=ui.control_active, fg=ui.text, relief=tk.FLAT, padx=8, pady=4)
        self._play.pack(side=tk.LEFT)
        self._refresh = tk.Button(buttons, text="Refresh cities", command=handler.request_city_refresh,
                                  bg=ui.control_background, fg=ui.text, relief=tk.FLAT, padx=8, pady=4)
        self._refresh.pack(side=tk.RIGHT)
        self._status = self._label(parent, "")
        self._label(parent, "Recent history = model estimates. Precip = rain + snow water equivalent.\nPan or zoom to choose cities · Data: Open-Meteo")
        self.set_state(state)

    def _row(self, parent):
        row = tk.Frame(parent, bg=self._ui.control_background)
        row.pack(fill=tk.X, pady=3)
        return row

    def _radio(self, parent, variable, value, text):
        tk.Radiobutton(parent, text=text, variable=variable, value=value, command=self._select,
                       bg=self._ui.control_background, fg=self._ui.text, selectcolor=self._ui.background,
                       activebackground=self._ui.control_background, activeforeground=self._ui.text,
                       font=("Sans", FONT_CONTROL)).pack(side=tk.LEFT)

    def _label(self, parent, text):
        label = tk.Label(parent, text=text, bg=self._ui.control_background, fg=self._ui.text,
                         font=("Sans", FONT_CONTROL), wraplength=340, anchor="w", justify=tk.LEFT)
        label.pack(fill=tk.X, pady=3)
        return label

    def _select(self):
        self._handler.request_city_selection(self._kind.get(), self._period.get(), self._state.hours)

    def _scrub(self, value):
        hours = int(float(value))
        if not self._updating and hours != self._state.hours:
            self._handler.request_city_selection(self._state.kind, self._state.period, hours)

    def set_state(self, state: CityWeatherOverlayState):
        """Synchronize playback and time without turning Scale.set into a user scrub."""
        self._updating = True
        try:
            self._state = state
            self._enabled.set(state.enabled)
            self._kind.set(state.kind)
            self._period.set(state.period)
            self._hours.set(state.hours)
            self._scale.configure(state=tk.NORMAL if state.enabled else tk.DISABLED)
            self._time.configure(text=city_time_label(state))
            self._status.configure(text=state.status)
            self._play.configure(text="Pause" if state.playing else "Play",
                                 state=tk.NORMAL if state.can_play else tk.DISABLED)
            self._refresh.configure(state=tk.NORMAL if state.can_refresh else tk.DISABLED)
        finally:
            self._updating = False
