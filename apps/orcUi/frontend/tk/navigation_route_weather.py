# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk weather controls consume immutable UI state and emit semantic requests."""

import tkinter as tk
from tkinter import ttk

from ui.weather.weather_overlay_controls_if import WeatherOverlayControlsIf
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState, ModelWeatherOverlayState, RouteWeatherOverlayState
from frontends.common.weather_overlay_format import city_time_label, model_legend, model_status, route_weather_label
from .shell_metrics import FONT_CONTROL
from .city_weather_controls import CityWeatherControls


class NavigationRouteWeather(WeatherOverlayControlsIf):
    """Own weather widgets only; providers, workers and map commands stay outside Tk."""

    def __init__(self, host, theme, unit_system):
        self._host, self._theme, self._unit_system = host, theme, unit_system
        self._handler: WeatherOverlayRequestHandlerIf | None = None
        self._city_state = CityWeatherOverlayState()
        self._model_state = ModelWeatherOverlayState()
        self._route_state = RouteWeatherOverlayState()
        self._panel = self._popup = self._city_banner = None

    def set_weather_overlay_request_handler(self, handler: WeatherOverlayRequestHandlerIf | None):
        """Connect a contract-implementing request consumer to the controls."""
        if handler is not None and not isinstance(handler, WeatherOverlayRequestHandlerIf):
            raise TypeError("Weather controls require WeatherOverlayRequestHandlerIf")
        self._handler = handler

    def set_city_weather_state(self, state):
        self._city_state = state
        self._render()

    def set_model_weather_state(self, state):
        self._model_state = state
        self._render()

    def set_route_weather_state(self, state):
        self._route_state = state
        self._render()

    def attach(self, panel):
        """Attach a compact menu and a caption without changing map height."""
        self._panel = panel
        panel.set_weather_menu_callbacks(self._render, self._close_popup)
        ui = self._theme().ui
        self._button = tk.Button(panel.weather_controls_parent, text="Weather ▾", command=self._toggle_popup,
                                 bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
                                 font=("Sans", FONT_CONTROL), padx=6)
        self._button.pack(side=tk.RIGHT, padx=4)
        self._city_banner = tk.Label(panel.weather_caption_parent, bg=ui.control_background, fg=ui.text,
                                     font=("Sans", 8), justify=tk.LEFT, anchor="w", padx=8, pady=5)
        if self._handler is not None:
            self._handler.request_navigation_visible(True)
        self._render()
        for delay in (300, 1200, 2500, 5000, 10000):
            self._host.schedule_ui_callback(delay, self._replay_if_visible)

    def hide(self):
        """Dismiss transient widgets and emit navigation lifecycle intent."""
        self._close_popup()
        if self._city_banner is not None:
            try:
                self._city_banner.destroy()
            except tk.TclError:
                pass
            self._city_banner = None
        if self._panel is not None:
            self._panel.set_weather_menu_callbacks(None, None)
        self._panel = None
        if self._handler is not None:
            self._handler.request_navigation_visible(False)

    def close(self):
        """Disconnect the view; the application composition owns controller cleanup."""
        self.hide()
        self._handler: WeatherOverlayRequestHandlerIf | None = None

    def _replay_if_visible(self):
        if self._panel is not None and self._handler is not None:
            self._handler.request_replay()

    def _toggle_popup(self):
        if self._popup is not None:
            self._close_popup()
            return
        self._panel.close_radar_menu()
        ui = self._theme().ui
        popup = self._popup = tk.Toplevel(self._panel, bg=ui.control_background)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self._panel.winfo_toplevel())
        body = tk.Frame(popup, bg=ui.control_background, padx=12, pady=8)
        body.pack(fill=tk.BOTH, expand=True)

        def label(text, parent=None):
            item = tk.Label(parent or body, text=text, bg=ui.control_background, fg=ui.text,
                            font=("Sans", FONT_CONTROL), anchor="w", justify=tk.LEFT, wraplength=330)
            item.pack(fill=tk.X, pady=2)
            return item

        title = tk.Frame(body, bg=ui.control_background)
        title.pack(fill=tk.X)
        tk.Label(title, text="Weather", bg=ui.control_background,
                 fg=ui.text, font=("Sans", FONT_CONTROL, "bold")).pack(side=tk.LEFT)
        tk.Button(title, text="×", command=self._close_popup, relief=tk.FLAT,
                  bg=ui.control_active, fg=ui.text).pack(side=tk.RIGHT)

        def toggle(text, var, command, parent=None, horizontal=False):
            tk.Checkbutton(parent or body, text=text, variable=var, command=command, bg=ui.control_background,
                           fg=ui.text, selectcolor=ui.background, activebackground=ui.control_background,
                           activeforeground=ui.text, font=("Sans", FONT_CONTROL)).pack(side=tk.LEFT if horizontal else tk.TOP, anchor="w")

        style = ttk.Style(popup)
        style.configure("Weather.TNotebook", background=ui.control_background, borderwidth=0)
        style.configure("Weather.TNotebook.Tab", background=ui.control_background,
                        foreground=ui.text, font=("Sans", FONT_CONTROL), padding=(8, 5))
        style.map("Weather.TNotebook.Tab", background=[("selected", ui.control_active)],
                  foreground=[("selected", ui.control_text)])
        tabs = ttk.Notebook(body, style="Weather.TNotebook")
        tabs.pack(fill=tk.BOTH, expand=True, pady=4)
        map_tab = tk.Frame(tabs, bg=ui.control_background)
        route_tab = tk.Frame(tabs, bg=ui.control_background)
        tabs.add(map_tab, text="Map overlays")
        tabs.add(route_tab, text="Along my route")
        self._city_controls = None
        if self._handler is not None:
            city_tab = tk.Frame(tabs, bg=ui.control_background)
            tabs.add(city_tab, text="City weather")
            self._city_controls = CityWeatherControls(city_tab, self._handler, self._city_state, ui)
        self._radar_var = tk.BooleanVar(popup, value=self._panel.radar_enabled)
        toggle("Radar overlay", self._radar_var, self._toggle_radar, map_tab)
        self._map_var = tk.StringVar(popup, value=self._model_state.kind)
        label("Model heatmap · one at a time", map_tab)
        for value, text in (("off", "No model heatmap"), ("temperature", "Temperature"),
                            ("wind", "Wind speed")):
            tk.Radiobutton(map_tab, text=text, variable=self._map_var, value=value,
                           command=self._select_map_weather, bg=ui.control_background, fg=ui.text,
                           selectcolor=ui.background, activebackground=ui.control_background,
                           font=("Sans", FONT_CONTROL), state=tk.NORMAL if self._handler else tk.DISABLED).pack(anchor="w")
        self._map_status = label("", map_tab)
        self._legend = tk.Frame(map_tab, bg=ui.control_background)
        self._legend.pack(fill=tk.X, pady=4)
        tk.Button(map_tab, text="Refresh model overlay", command=self._refresh_map_weather,
                  bg=ui.control_active, fg=ui.text, relief=tk.FLAT, pady=4).pack(anchor="w", pady=3)
        label("Contiguous United States only", map_tab)
        body = route_tab
        self._enabled_var = tk.BooleanVar(popup, value=self._route_state.enabled)
        toggle("Weather on my route", self._enabled_var, self._set_enabled)
        self._layer_vars = {}
        layer_row = tk.Frame(body, bg=ui.control_background)
        layer_row.pack(fill=tk.X)
        for key, text in (("temperature", "Temp"), ("rain", "Precip %"), ("wind", "Wind")):
            var = self._layer_vars[key] = tk.BooleanVar(popup, value=key in self._route_state.layers)
            toggle(text, var, self._set_layers, layer_row, horizontal=True)
        label("Forecasts at estimated arrivals · no live traffic or stops")
        self._status_label = label(self._route_state.status)
        details = tk.Frame(body, bg=ui.control_background)
        details.pack(fill=tk.X, pady=3)
        self._details = tk.Text(details, height=6, width=42, wrap=tk.WORD,
                                bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
                                font=("Sans", FONT_CONTROL), state=tk.DISABLED)
        scrollbar = tk.Scrollbar(details, command=self._details.yview)
        self._details.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Button(body, text="Refresh route forecast", command=self._refresh_route_weather, relief=tk.FLAT,
                  bg=ui.control_active, fg=ui.text, pady=5).pack(anchor="w", pady=4)
        self._tabs = tabs
        popup.bind("<Escape>", lambda _event: self._close_popup())
        self._render()
        popup.update_idletasks()
        x = self._button.winfo_rootx() + self._button.winfo_width() - popup.winfo_reqwidth()
        y = self._button.winfo_rooty() + self._button.winfo_height() + 4
        popup.geometry(f"+{max(0, x)}+{max(0, y)}")
        popup.deiconify()
        popup.lift()

    def _select_map_weather(self):
        if self._handler is not None:
            self._handler.request_model_selection(self._map_var.get())

    def _refresh_map_weather(self):
        if self._handler is not None:
            self._handler.request_model_refresh()

    def _refresh_route_weather(self):
        if self._handler is not None:
            self._handler.request_route_refresh()

    def _set_enabled(self):
        if self._handler is not None:
            self._handler.request_route_enabled(self._enabled_var.get())

    def _set_layers(self):
        if self._handler is not None:
            self._handler.request_route_layers(frozenset(key for key, var in self._layer_vars.items() if var.get()))

    def _toggle_radar(self):
        self._panel.set_radar_enabled(self._radar_var.get())

    def _render(self):
        if self._city_banner is not None:
            cities = self._city_state
            if cities.enabled:
                field = {"temperature": "TEMPERATURE", "wind": "WIND SPEED", "precipitation": "PRECIPITATION"}[cities.kind]
                period = "RECENT HISTORY · Model estimates" if cities.period == "past" else "FORECAST"
                caption = city_time_label(cities) if cities.points else cities.status.split(":")[0]
                self._city_banner.configure(text=f"{field} · {period}\n{caption}",
                                            wraplength=max(140, min(380, self._panel.map_width - 32)))
                self._city_banner.place(x=12, y=8)
                self._city_banner.lift()
            else:
                self._city_banner.place_forget()
        if self._popup is None:
            return
        if self._city_controls is not None:
            self._city_controls.set_state(self._city_state)
        if self._handler is not None:
            self._map_status.configure(text=model_status(self._model_state))
            for child in self._legend.winfo_children():
                child.destroy()
            for label, rgb in model_legend(self._model_state, self._unit_system().value == "imperial"):
                tk.Label(self._legend, text=label, bg="#" + "".join(f"{v:02x}" for v in rgb),
                         fg="#ffffff" if sum(c * w for c, w in zip(rgb, (0.299, 0.587, 0.114))) < 140 else "#101820",
                         font=("Sans", 8), padx=2, pady=4).pack(side=tk.LEFT)
        self._status_label.configure(text=self._route_state.status)
        self._radar_var.set(self._panel.radar_enabled)
        lines = []
        for index, forecast in enumerate(self._route_state.points, 1):
            arrival = forecast.arrival.astimezone().strftime("%I:%M %p").lstrip("0")
            lines.append(f"{index} · ~{arrival} · {forecast.condition}\n{route_weather_label(forecast, self._route_state.layers, self._unit_system().value == 'imperial')}")
        self._details.configure(state=tk.NORMAL)
        self._details.delete("1.0", tk.END)
        self._details.insert("1.0", "\n".join(lines))
        self._details.configure(state=tk.DISABLED)

    def _close_popup(self):
        if self._popup is not None:
            try:
                self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None
