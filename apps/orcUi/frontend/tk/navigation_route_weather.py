# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk weather controls consume immutable UI state and emit semantic requests."""

import tkinter as tk
from functools import partial
from frontends.tk.touch_button import TouchButton

from ui.weather.weather_overlay_controls_if import WeatherOverlayControlsIf
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState, ModelWeatherOverlayState, RouteWeatherOverlayState
from frontends.common.weather_overlay_format import city_time_label, model_legend, model_status, route_weather_label
from .shell_metrics import FONT_CONTROL
from .city_weather_controls import CityWeatherControls
from .city_weather_details_popup import CityWeatherDetailsPopup
from ui.ui_widget import UiWidget


class NavigationRouteWeather(WeatherOverlayControlsIf, UiWidget):
    """Own weather widgets only; providers, workers and map commands stay outside Tk."""

    def __init__(self, host, theme, unit_system):
        self._host, self._theme, self._unit_system = host, theme, unit_system
        self._handler: WeatherOverlayRequestHandlerIf | None = None
        self._city_state = CityWeatherOverlayState()
        self._model_state = ModelWeatherOverlayState()
        self._route_state = RouteWeatherOverlayState()
        self._panel = self._popup = self._city_banner = None
        self._city_details_popup = None
        self._city_controls = None

    def set_weather_overlay_request_handler(self, handler: WeatherOverlayRequestHandlerIf | None):
        """Connect a contract-implementing request consumer to the controls."""
        if handler is not None and not isinstance(handler, WeatherOverlayRequestHandlerIf):
            raise TypeError("Weather controls require WeatherOverlayRequestHandlerIf")
        if handler is not self._handler:
            self._close_popup()
            self._destroy_city_details()
        self._handler = handler

    def set_city_weather_state(self, state):
        self._city_state = state
        self._render()
        self._render_city_details()

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
                                 bd=0, highlightthickness=0,
                                 font=("Sans", FONT_CONTROL), padx=6)
        self._button.pack(side=tk.RIGHT, padx=4)
        self._city_banner = tk.Label(panel.weather_caption_parent, bg=ui.control_background, fg=ui.text,
                                     font=("Sans", 10), justify=tk.LEFT, anchor="w", padx=8, pady=5)
        if self._handler is not None:
            self._handler.request_navigation_visible(True)
        self._render()
        self._render_city_details()
        for delay in (300, 1200, 2500, 5000, 10000):
            self._host.schedule_ui_callback(delay, self._replay_if_visible)

    def hide(self):
        """Dismiss transient widgets and emit navigation lifecycle intent."""
        self._close_popup()
        self._destroy_city_details()
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

    def _destroy_city_details(self):
        if self._city_details_popup is not None:
            self._city_details_popup.destroy()
            self._city_details_popup = None

    def _close_city_details(self):
        if self._handler is not None:
            self._handler.request_city_details(None)
        self._destroy_city_details()

    def _render_city_details(self):
        state = self._city_state
        if self._panel is None or not state.enabled or not state.visible or state.details is None:
            self._destroy_city_details()
            return
        if self._city_details_popup is None:
            self._close_popup()
            self._panel.close_radar_menu()
            self._city_details_popup = CityWeatherDetailsPopup(
                self._panel, state, ui=self._theme().ui,
                imperial=lambda: self._unit_system().value == "imperial", on_close=self._close_city_details)
        else:
            self._city_details_popup.render(state)

    def _replay_if_visible(self):
        if self._panel is not None and self._handler is not None:
            self._handler.request_replay()

    def _toggle_popup(self):
        if self._popup is not None:
            self._close_popup()
            return
        if self._panel is None:
            return
        self._panel.close_radar_menu()
        ui = self._theme().ui
        popup = self._popup = tk.Toplevel(self._panel, bg=ui.control_background)
        popup.withdraw()
        popup.overrideredirect(True)
        root = self._panel.winfo_toplevel()
        popup.transient(root)
        self._weather_compact = False
        body = self._popup_body = tk.Frame(popup, bg=ui.control_background, padx=12, pady=10)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=1)

        def label(parent, text, *, height=0):
            item = tk.Label(parent, text=text, bg=ui.control_background, fg=ui.text,
                            font=("Sans", 11), anchor="w", justify=tk.LEFT,
                            wraplength=580, height=height)
            item.pack(fill=tk.X, pady=3)
            return item

        def button(parent, text, command, *, width=None):
            return TouchButton(parent, text, command, ui, width)

        title = tk.Frame(body, bg=ui.control_background)
        title.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(title, text="Weather controls", bg=ui.control_background,
                 fg=ui.text, font=("Sans", 14, "bold")).pack(side=tk.LEFT)
        button(title, "Close  ×", self._close_popup, width=110).pack(side=tk.RIGHT)
        tabs = tk.Frame(body, bg=ui.control_background)
        tabs.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self._weather_tabs = {}
        self._weather_pages = {}
        for column, (key, caption) in enumerate((("map", "Map"), ("route", "Route"), ("cities", "Cities"))):
            tabs.grid_columnconfigure(column, weight=1, uniform="weather-tabs")
            tab = button(tabs, caption, partial(self._show_weather_tab, key))
            tab.grid(row=0, column=column, sticky="ew", padx=3)
            self._weather_tabs[key] = tab
            page = tk.Frame(body, bg=ui.control_background)
            page.grid(row=2, column=0, sticky="nsew")
            self._weather_pages[key] = page
        map_tab, route_tab, city_tab = (self._weather_pages[key] for key in ("map", "route", "cities"))
        self._radar_var = tk.BooleanVar(popup, value=self._panel.radar_enabled)
        self._radar_toggle = button(map_tab, "Radar overlay", partial(self._toggle_value, self._radar_var, self._toggle_radar))
        self._radar_toggle.pack(fill=tk.X, pady=3)
        self._map_var = tk.StringVar(popup, value=self._model_state.kind)
        label(map_tab, "Model forecast · choose one heatmap")
        choices = tk.Frame(map_tab, bg=ui.control_background)
        choices.pack(fill=tk.X, pady=3)
        self._model_buttons = {}
        for column, (kind, caption) in enumerate((("off", "Off"), ("temperature", "Temperature"), ("wind", "Wind speed"))):
            choices.grid_columnconfigure(column, weight=1, uniform="model-choices")
            choice = button(choices, caption, partial(self._choose_model, kind) if self._handler else None)
            choice.grid(row=0, column=column, sticky="ew", padx=3)
            self._model_buttons[kind] = (choice, caption)
        self._map_status = label(map_tab, "", height=2)
        self._legend = tk.Frame(map_tab, bg=ui.control_background)
        self._legend.pack(fill=tk.X, pady=4)
        button(map_tab, "Refresh model overlay", self._refresh_map_weather if self._handler else None).pack(fill=tk.X, pady=4)
        label(map_tab, "Model overlays cover the contiguous United States.")
        self._enabled_var = tk.BooleanVar(popup, value=self._route_state.enabled)
        self._route_toggle = button(route_tab, "Weather on my route", partial(self._toggle_value, self._enabled_var, self._set_enabled) if self._handler else None)
        self._route_toggle.pack(fill=tk.X, pady=3)
        self._layer_vars, self._layer_buttons = {}, {}
        layer_row = tk.Frame(route_tab, bg=ui.control_background)
        layer_row.pack(fill=tk.X, pady=3)
        for column, (key, caption) in enumerate((("temperature", "Temperature"), ("rain", "Precip %"), ("wind", "Wind"))):
            var = self._layer_vars[key] = tk.BooleanVar(popup, value=key in self._route_state.layers)
            layer_row.grid_columnconfigure(column, weight=1, uniform="route-layers")
            choice = button(layer_row, caption, partial(self._toggle_value, var, self._set_layers) if self._handler else None)
            choice.grid(row=0, column=column, sticky="ew", padx=3)
            self._layer_buttons[key] = (choice, caption)
        label(route_tab, "Weather at estimated arrivals · no live traffic or stops")
        self._status_label = label(route_tab, "", height=2)
        details = tk.Frame(route_tab, bg=ui.control_background)
        details.pack(fill=tk.X, pady=3)
        self._details = tk.Text(details, height=4, width=1, wrap=tk.WORD,
            bg=ui.control_background, fg=ui.text, relief=tk.FLAT, font=("Sans", 12),
            state=tk.DISABLED, bd=0, highlightthickness=0)
        arrows = tk.Frame(details, bg=ui.control_background)
        arrows.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        for text, delta in (("▲", -3), ("▼", 3)):
            button(arrows, text, lambda amount=delta: self._details.yview_scroll(amount, "units"), width=56).pack()
        self._details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        button(route_tab, "Refresh route forecast", self._refresh_route_weather if self._handler else None).pack(fill=tk.X, pady=4)
        if self._handler is not None:
            self._city_controls = CityWeatherControls(city_tab, self._handler, self._city_state, ui)
        else:
            label(city_tab, "City weather is unavailable.")
        self._city_playback_bar = tk.Frame(popup, bg=ui.control_background, padx=12, pady=6)
        self._city_playback_time = tk.Label(self._city_playback_bar, bg=ui.control_background,
            fg=ui.text, font=("Sans", 13), anchor="w", wraplength=480)
        self._city_playback_time.pack(side=tk.LEFT, fill=tk.X, expand=True)
        button(self._city_playback_bar, "■ Stop", self._stop_city_playback, width=110).pack(side=tk.RIGHT)
        popup.bind("<Escape>", lambda _event: self._close_popup())
        popup.bind("<Button-1>", self._outside_popup_press, add="+")
        self._show_weather_tab("map")
        self._render()
        popup.update_idletasks()
        self._position_weather_popup()
        popup.deiconify()
        popup.lift()
        if not self._weather_compact:
            popup.grab_set()
            popup.focus_set()

    def _show_weather_tab(self, key):
        self._weather_tab = key
        self._weather_pages[key].tkraise()
        for name, tab in self._weather_tabs.items():
            tab.configure_button(selected=name == key)
        self._render()

    def _set_city_compact(self, compact):
        if compact == self._weather_compact:
            return
        self._weather_compact = compact
        popup = self._popup
        if compact:
            self._popup_body.pack_forget()
            self._city_playback_bar.pack(fill=tk.BOTH, expand=True)
            if popup.grab_current() is popup:
                popup.grab_release()
        else:
            self._city_playback_bar.pack_forget()
            self._popup_body.pack(fill=tk.BOTH, expand=True)
            popup.grab_set()
            popup.focus_set()
        popup.update_idletasks()
        self._position_weather_popup()

    def _position_weather_popup(self):
        popup = self._popup
        owner = self._panel if self._weather_compact else self._panel.winfo_toplevel()
        width = min(720 if self._weather_compact else 660,
                    max(280, owner.winfo_width() - 24), popup.winfo_screenwidth() - 12)
        height = min(popup.winfo_reqheight(), popup.winfo_screenheight() - 24)
        x = max(0, min(owner.winfo_rootx() + (owner.winfo_width() - width) // 2, popup.winfo_screenwidth() - width))
        desired_y = (owner.winfo_rooty() + owner.winfo_height() - height - 12 if self._weather_compact
                     else owner.winfo_rooty() + (owner.winfo_height() - height) // 2)
        y = max(0, min(desired_y, popup.winfo_screenheight() - height))
        popup.geometry(f"{width}x{height}+{x}+{y}")

    def _stop_city_playback(self):
        if self._popup is not None and self._handler is not None:
            self._handler.request_city_playback(False)

    def _outside_popup_press(self, event):
        popup = self._popup
        if popup is not None and not (popup.winfo_rootx() <= event.x_root < popup.winfo_rootx() + popup.winfo_width()
                and popup.winfo_rooty() <= event.y_root < popup.winfo_rooty() + popup.winfo_height()):
            self._close_popup()
            return "break"

    def _toggle_value(self, variable, callback):
        if self._popup is not None:
            variable.set(not variable.get())
            callback()

    def _choose_model(self, kind):
        if self._popup is not None:
            self._map_var.set(kind)
            self._select_map_weather()

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
                period = "RECENT HISTORY · Estimated weather" if cities.period == "past" else "FORECAST"
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
                         font=("Sans", 10), padx=4, pady=6).pack(side=tk.LEFT)
        self._map_var.set(self._model_state.kind)
        self._enabled_var.set(self._route_state.enabled)
        self._radar_toggle.configure_button(selected=self._panel.radar_enabled,
            text="✓ Radar overlay on" if self._panel.radar_enabled else "Radar overlay off")
        self._route_toggle.configure_button(selected=self._route_state.enabled,
            text="✓ Weather on my route" if self._route_state.enabled else "Weather on my route")
        for kind, (button, caption) in self._model_buttons.items():
            selected = kind == self._model_state.kind
            button.configure_button(selected=selected, text=f"✓ {caption}" if selected else caption)
        for key, (button, caption) in self._layer_buttons.items():
            selected = key in self._route_state.layers
            self._layer_vars[key].set(selected)
            button.configure_button(selected=selected, text=f"✓ {caption}" if selected else caption)
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
        self._city_playback_time.configure(text=city_time_label(self._city_state))
        self._set_city_compact(self._weather_tab == "cities" and self._city_state.enabled and self._city_state.playing)

    def _close_popup(self):
        popup, self._popup = self._popup, None
        if self._city_controls is not None:
            self._city_controls.close()
            self._city_controls = None
        if popup is not None:
            try:
                if popup.grab_current() is popup:
                    popup.grab_release()
                popup.destroy()
            except tk.TclError:
                pass
