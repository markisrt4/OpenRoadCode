# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-friendly city weather selection and independent playback."""
import tkinter as tk
from functools import partial

from frontends.tk.touch_button import TouchButton
from ui.ui_widget import UiWidget
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState
from frontends.common.weather_overlay_format import city_time_label


class CityWeatherControls(UiWidget):
    """Render city snapshots and emit explicit, toolkit-independent requests."""

    def __init__(self, parent, handler: WeatherOverlayRequestHandlerIf, state: CityWeatherOverlayState, ui):
        self._handler, self._state, self._ui = handler, state, ui
        self._updating = False
        self._hours = tk.DoubleVar(parent, value=state.hours)
        self._enabled = TouchButton(parent, 'City weather', self._toggle_enabled, ui)
        self._enabled.pack(fill=tk.X, pady=3)
        self._fields = self._choices(parent, (
            ('temperature', 'Temperature'), ('wind', 'Wind speed'), ('precipitation', 'Precip total')),
            self._select_field)
        self._periods = self._choices(parent, (('past', 'Recent history'), ('future', 'Forecast')),
                                     self._select_period)
        self._scale = tk.Scale(parent, from_=1, to=24, resolution=1, orient=tk.HORIZONTAL,
            variable=self._hours, command=self._scrub, label='Hours', showvalue=True,
            bg=ui.control_background, fg=ui.text, troughcolor=ui.background,
            highlightthickness=0, bd=0, sliderlength=48, width=24,
            font=('Sans', 12), activebackground=ui.border)
        self._scale.pack(fill=tk.X, pady=3)
        self._time = self._label(parent, '')
        actions = tk.Frame(parent, bg=ui.control_background)
        actions.pack(fill=tk.X, pady=3)
        self._play = TouchButton(actions, '▶ Play', self._toggle_playback, ui)
        self._refresh = TouchButton(actions, 'Refresh cities', self._refresh_cities, ui)
        for column, item in enumerate((self._play, self._refresh)):
            actions.grid_columnconfigure(column, weight=1, uniform='city-actions')
            item.grid(row=0, column=column, sticky='ew', padx=3)
        self._status = self._label(parent, '', height=2)
        self._label(parent, 'Recent history uses model estimates. Precipitation includes melted snow.\n'
                    'Pan/zoom to choose cities · Provider: Open-Meteo')
        self.set_state(state)

    def _choices(self, parent, choices, callback):
        row = tk.Frame(parent, bg=self._ui.control_background)
        row.pack(fill=tk.X, pady=3)
        buttons = {}
        for column, (value, caption) in enumerate(choices):
            row.grid_columnconfigure(column, weight=1, uniform='city-choices')
            button = TouchButton(row, caption, partial(callback, value), self._ui)
            button.grid(row=0, column=column, sticky='ew', padx=3)
            buttons[value] = (button, caption)
        return buttons

    def _label(self, parent, text, *, height=0):
        label = tk.Label(parent, text=text, bg=self._ui.control_background, fg=self._ui.text,
            font=('Sans', 11), wraplength=580, anchor='w', justify=tk.LEFT, height=height)
        label.pack(fill=tk.X, pady=3)
        return label

    def _toggle_enabled(self):
        if self._handler is not None:
            self._handler.request_city_enabled(not self._state.enabled)

    def _select_field(self, kind):
        if self._handler is not None:
            self._handler.request_city_selection(kind, self._state.period, self._state.hours)

    def _select_period(self, period):
        if self._handler is not None:
            self._handler.request_city_selection(self._state.kind, period, self._state.hours)

    def _toggle_playback(self):
        if self._handler is not None:
            self._handler.request_city_playback(not self._state.playing)

    def _refresh_cities(self):
        if self._handler is not None:
            self._handler.request_city_refresh()

    def _scrub(self, value):
        hours = int(float(value))
        if self._handler is not None and not self._updating and hours != self._state.hours:
            self._handler.request_city_selection(self._state.kind, self._state.period, hours)

    def set_state(self, state: CityWeatherOverlayState):
        """Synchronize selected buttons and slider without emitting requests."""
        self._updating = True
        try:
            self._state = state
            self._hours.set(state.hours)
            self._enabled.configure_button(selected=state.enabled,
                text='✓ City weather on' if state.enabled else 'City weather off')
            for buttons, selected in ((self._fields, state.kind), (self._periods, state.period)):
                for value, (button, caption) in buttons.items():
                    active = value == selected
                    button.configure_button(selected=active, text=f'✓ {caption}' if active else caption)
            self._scale.configure(state=tk.NORMAL if state.enabled else tk.DISABLED)
            self._time.configure(text=city_time_label(state))
            self._status.configure(text=state.status)
            self._play.configure_button(text='Ⅱ Pause' if state.playing else '▶ Play',
                selected=state.playing, state=tk.NORMAL if state.can_play else tk.DISABLED)
            self._refresh.configure_button(state=tk.NORMAL if state.can_refresh else tk.DISABLED)
        finally:
            self._updating = False

    def close(self):
        """Retire actions before the popup's widgets are destroyed."""
        self._handler = None
