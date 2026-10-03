# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Collapsible route forecast and independently selectable map labels."""

from datetime import datetime, timezone
import threading
import tkinter as tk
from tkinter import ttk

from controllers.weather.route_weather import RouteWeatherProvider, sample_route
from .shell_metrics import FONT_CONTROL


class NavigationRouteWeather:
    """Keep route weather requests off the UI thread and reject stale results."""

    def __init__(self, host, route_handler, map_renderer, theme, unit_system, presentation, map_weather=None):
        self._map_weather = map_weather
        if map_weather is not None:
            map_weather.on_changed = self._render
        self._host = host
        self._renderer = map_renderer
        self._theme = theme
        self._unit_system = unit_system
        self._provider = RouteWeatherProvider()
        self._route = route_handler.active_route
        self._progress = 0
        self._generation = 0
        self._enabled = False
        self._layers = {"temperature", "rain", "wind"}
        self._forecasts = ()
        self._status = "Start a route to see weather along the way"
        self._panel = None
        self._popup = None
        self._busy = False
        self._closed = False
        self._poll_generation = 0
        route_handler.observe_route(self._route_changed)
        presentation.observe_route_guidance(self._guidance_changed)

    def _route_changed(self, route):
        self._generation += 1
        self._route = route
        self._progress = 0
        self._forecasts = ()
        self._publish()
        self._status = "Start a route to see weather along the way" if route is None else "Route ready"
        self._render()
        if self._enabled and route is not None:
            self.refresh()

    def _guidance_changed(self, message):
        data = message.data
        if data.route_complete:
            self._route_changed(None)
            return
        total = data.distance_along_route_m + data.distance_remaining_m
        self._progress = max(0, min(1, data.distance_along_route_m / total)) if total > 0 else 0

    def attach(self, panel):
        """Add a small layers button without taking height away from the map."""
        self._panel = panel
        panel._on_weather_visibility_changed = self._render
        panel._close_weather_menu = self._close_popup
        ui = self._theme().ui
        self._button = tk.Button(panel._radar_button.master, text="Weather ▾", command=self._toggle_popup,
                                 bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
                                 font=("Sans", FONT_CONTROL), padx=6)
        self._button.pack(side=tk.RIGHT, padx=4)
        self._poll_generation += 1
        self._poll(self._poll_generation)
        for delay in (300, 1200, 2500, 5000, 10000):
            self._host.schedule_ui_callback(delay, self._publish_if_visible)

    def hide(self):
        """Dismiss the menu and cancel automatic refresh while Navigation is hidden."""
        self._close_popup()
        if self._panel is not None:
            self._panel._on_weather_visibility_changed = None
            self._panel._close_weather_menu = None
        self._panel = None
        self._poll_generation += 1

    def close(self):
        """Invalidate late work and close the forecast connection pool."""
        self._closed = True
        self._generation += 1
        self.hide()
        self._provider.close()
        if self._map_weather is not None:
            self._map_weather.close()

    def _poll(self, generation):
        if self._panel is None or generation != self._poll_generation:
            return
        if self._enabled and self._route is not None:
            self.refresh()
        if self._map_weather is not None:
            self._map_weather.refresh()
        self._host.schedule_ui_callback(900000, lambda: self._poll(generation))

    def refresh(self):
        """Fetch the remaining route at estimated arrival times with one batch request."""
        if self._closed or not self._enabled or self._route is None:
            return
        if self._busy:
            return
        self._busy = True
        generation = self._generation
        route, progress = self._route, self._progress
        self._status = "Loading route forecast…"
        self._render()

        def load():
            try:
                points = sample_route(route, datetime.now(timezone.utc), progress)
                forecasts = self._provider.forecast(points)
                error = None
            except Exception as failure:
                forecasts, error = (), str(failure)
            if not self._closed:
                self._host.schedule_ui_callback(0, lambda: self._complete(generation, forecasts, error))

        threading.Thread(target=load, name="route-weather", daemon=True).start()

    def _complete(self, generation, forecasts, error):
        self._busy = False
        if self._closed:
            return
        if generation != self._generation or not self._enabled:
            if self._enabled and self._route is not None:
                self.refresh()
            return
        if error:
            self._forecasts = ()
            self._status = f"Forecast unavailable: {error}"
        else:
            self._forecasts = forecasts
            self._status = f"Updated {datetime.now().strftime('%I:%M %p').lstrip('0')} · Open-Meteo"
        self._publish()
        self._render()

    def _set_enabled(self):
        self._enabled = self._enabled_var.get()
        self._generation += 1
        self._forecasts = ()
        self._publish()
        self._status = "Route weather off" if not self._enabled else "Start a route to load forecasts"
        self._render()
        if self._enabled:
            self.refresh()

    def _set_layers(self):
        self._layers = {key for key, var in self._layer_vars.items() if var.get()}
        self._publish()
        self._render()

    def _labels(self, forecast):
        values = []
        imperial = getattr(self._unit_system(), "value", "") == "imperial"
        if "temperature" in self._layers:
            value = forecast.temperature_c
            text = "Temp —" if value is None else (f"{value * 9 / 5 + 32:.0f}°F" if imperial else f"{value:.0f}°C")
            values.append(text)
        if "rain" in self._layers:
            values.append("Precip —" if forecast.rain_probability is None else f"Precip {forecast.rain_probability:.0f}%")
        if "wind" in self._layers:
            value = forecast.wind_kmh
            values.append("Wind —" if value is None else
                          (f"Wind {value / 1.609344:.0f} mph" if imperial else f"Wind {value:.0f} km/h"))
        return " · ".join(values)

    def _publish_if_visible(self):
        if self._panel is not None:
            self._publish()
            if self._map_weather is not None:
                self._map_weather.publish()

    def _publish(self):
        features = []
        if self._enabled and self._layers:
            for index, forecast in enumerate(self._forecasts, 1):
                point = forecast.checkpoint.point
                features.append({"type": "Feature", "geometry": {
                    "type": "Point", "coordinates": [point.longitude, point.latitude]},
                    "properties": {"label": f"{index} · ~{forecast.checkpoint.arrival.astimezone().strftime('%I:%M %p').lstrip('0')}\n{self._labels(forecast)}"}})
        self._renderer.set_route_weather({"type": "FeatureCollection", "features": features})

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
        self._radar_var = tk.BooleanVar(popup, value=self._panel._radar_enabled)
        toggle("Radar overlay", self._radar_var, self._toggle_radar, map_tab)
        self._map_var = tk.StringVar(popup, value=self._map_weather.kind if self._map_weather else "off")
        label("Model heatmap · one at a time", map_tab)
        for value, text in (("off", "No model heatmap"), ("temperature", "Temperature"),
                            ("wind", "Wind speed")):
            tk.Radiobutton(map_tab, text=text, variable=self._map_var, value=value,
                           command=self._select_map_weather, bg=ui.control_background, fg=ui.text,
                           selectcolor=ui.background, activebackground=ui.control_background,
                           font=("Sans", FONT_CONTROL), state=tk.NORMAL if self._map_weather else tk.DISABLED).pack(anchor="w")
        self._map_status = label("", map_tab)
        self._legend = tk.Frame(map_tab, bg=ui.control_background)
        self._legend.pack(fill=tk.X, pady=4)
        tk.Button(map_tab, text="Refresh model overlay", command=self._refresh_map_weather,
                  bg=ui.control_active, fg=ui.text, relief=tk.FLAT, pady=4).pack(anchor="w", pady=3)
        label("Contiguous United States only", map_tab)
        body = route_tab
        self._enabled_var = tk.BooleanVar(popup, value=self._enabled)
        toggle("Weather on my route", self._enabled_var, self._set_enabled)
        self._layer_vars = {}
        layer_row = tk.Frame(body, bg=ui.control_background)
        layer_row.pack(fill=tk.X)
        for key, text in (("temperature", "Temp"), ("rain", "Precip %"), ("wind", "Wind")):
            var = self._layer_vars[key] = tk.BooleanVar(popup, value=key in self._layers)
            toggle(text, var, self._set_layers, layer_row, horizontal=True)
        label("Forecasts at estimated arrivals · no live traffic or stops")
        self._status_label = label(self._status)
        details = tk.Frame(body, bg=ui.control_background)
        details.pack(fill=tk.X, pady=3)
        self._details = tk.Text(details, height=6, width=42, wrap=tk.WORD,
                                bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
                                font=("Sans", FONT_CONTROL), state=tk.DISABLED)
        scrollbar = tk.Scrollbar(details, command=self._details.yview)
        self._details.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Button(body, text="Refresh route forecast", command=self.refresh, relief=tk.FLAT,
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
        if self._map_weather is not None:
            self._map_weather.select(self._map_var.get())

    def _refresh_map_weather(self):
        if self._map_weather is not None:
            self._map_weather.refresh()

    def _toggle_radar(self):
        if self._panel._radar_enabled != self._radar_var.get():
            self._panel._toggle_radar()

    def _render(self):
        if self._popup is None:
            return
        if self._map_weather is not None:
            self._map_status.configure(text=self._map_weather.status)
            for child in self._legend.winfo_children():
                child.destroy()
            for label, rgb in self._map_weather.legend():
                tk.Label(self._legend, text=label, bg="#" + "".join(f"{v:02x}" for v in rgb),
                         fg="#ffffff" if sum(c * w for c, w in zip(rgb, (0.299, 0.587, 0.114))) < 140 else "#101820",
                         font=("Sans", 8), padx=2, pady=4).pack(side=tk.LEFT)
        self._status_label.configure(text=self._status)
        self._radar_var.set(self._panel._radar_enabled)
        lines = []
        for index, forecast in enumerate(self._forecasts, 1):
            arrival = forecast.checkpoint.arrival.astimezone().strftime("%I:%M %p").lstrip("0")
            lines.append(f"{index} · ~{arrival} · {forecast.condition}\n{self._labels(forecast)}")
        self._details.configure(state=tk.NORMAL)
        self._details.delete("1.0", tk.END)
        self._details.insert("1.0", "\n".join(lines))
        self._details.configure(state=tk.DISABLED)

    def _close_popup(self):
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None
