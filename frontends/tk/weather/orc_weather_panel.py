# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-friendly native Tk weather dashboard for orcUi."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from common.units import (
    UnitSystem,
    kelvin_to_celsius,
    kelvin_to_fahrenheit,
    meters_per_second_to_kilometers_per_hour,
    meters_per_second_to_miles_per_hour,
)
from ui.theme import ThemeBundle
from ui.weather import WeatherRequestHandlerIf, WeatherUiIf, WeatherUiState


class OrcWeatherPanel(tk.Frame, WeatherUiIf):
    """Render normalized weather state as an at-a-glance automotive dashboard."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        unit_system: Callable[[], UnitSystem] = lambda: UnitSystem.IMPERIAL,
        on_weather_radio: Callable[[], None] | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle
        self._unit_system = unit_system
        self._on_weather_radio = on_weather_radio
        self._handler: WeatherRequestHandlerIf | None = None
        self._state: WeatherUiState | None = None
        ui = theme_bundle().ui
        super().__init__(parent, bg=ui.background)

        self._header = tk.Frame(self, bg=ui.background)
        self._header.pack(fill=tk.X, padx=24, pady=(18, 8))
        self._location = tk.Label(self._header, text="Weather", anchor="w", font=("Sans", 20, "bold"))
        self._location.pack(side=tk.LEFT)
        self._provider = tk.Label(self._header, text="", anchor="e", font=("Sans", 10))
        self._provider.pack(side=tk.RIGHT, padx=(12, 0))
        self._refresh = tk.Button(self._header, text="Refresh", command=self._request_refresh, padx=14, pady=6)
        self._refresh.pack(side=tk.RIGHT)
        self._weather_radio = tk.Button(
            self._header,
            text="NOAA WEATHER RADIO",
            command=self._request_weather_radio,
            padx=14,
            pady=6,
        )
        self._weather_radio.pack(side=tk.RIGHT, padx=(0, 8))

        self._current_card = tk.Frame(self, bd=1, highlightthickness=1)
        self._current_card.pack(fill=tk.X, padx=24, pady=8)
        self._temperature = tk.Label(self._current_card, text="--°", font=("Sans", 52, "bold"), anchor="w")
        self._temperature.grid(row=0, column=0, rowspan=2, sticky="w", padx=(20, 30), pady=14)
        self._condition = tk.Label(self._current_card, text="Weather unavailable", font=("Sans", 22, "bold"), anchor="w")
        self._condition.grid(row=0, column=1, sticky="sw", padx=8, pady=(18, 2))
        self._details = tk.Label(self._current_card, text="", font=("Sans", 12), anchor="w")
        self._details.grid(row=1, column=1, sticky="nw", padx=8, pady=(2, 18))
        self._current_card.columnconfigure(1, weight=1)

        self._hourly_title = tk.Label(self, text="NEXT HOURS", font=("Sans", 11, "bold"), anchor="w")
        self._hourly_title.pack(fill=tk.X, padx=26, pady=(12, 4))
        self._hourly = tk.Frame(self)
        self._hourly.pack(fill=tk.X, padx=24)

        self._daily_title = tk.Label(self, text="FORECAST", font=("Sans", 11, "bold"), anchor="w")
        self._daily_title.pack(fill=tk.X, padx=26, pady=(14, 4))
        self._daily = tk.Frame(self)
        self._daily.pack(fill=tk.X, padx=24, pady=(0, 16))

        self.set_theme_bundle(theme_bundle())

    def set_weather_request_handler(self, handler: WeatherRequestHandlerIf | None) -> None:
        self._handler = handler

    def set_weather_state(self, state: WeatherUiState | None) -> None:
        self._state = state
        self._render()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        self._header.configure(bg=ui.background)
        self._location.configure(bg=ui.background, fg=ui.text)
        self._provider.configure(bg=ui.background, fg=ui.text_muted)
        for button in (self._refresh, self._weather_radio):
            button.configure(
                bg=ui.control_background, fg=ui.control_text,
                activebackground=ui.border, activeforeground=ui.text,
                relief=tk.FLAT,
            )
        self._current_card.configure(bg=ui.surface, highlightbackground=ui.border)
        for widget in (self._temperature, self._condition, self._details):
            widget.configure(bg=ui.surface)
        self._temperature.configure(fg=ui.text)
        self._condition.configure(fg=ui.text)
        self._details.configure(fg=ui.text_muted)
        for title in (self._hourly_title, self._daily_title):
            title.configure(bg=ui.background, fg=ui.text_muted)
        for frame in (self._hourly, self._daily):
            frame.configure(bg=ui.background)
        self._render_forecasts()

    def _request_refresh(self) -> None:
        if self._handler is not None:
            self._handler.request_refresh()

    def _request_weather_radio(self) -> None:
        if self._on_weather_radio is not None:
            self._on_weather_radio()

    def _render(self) -> None:
        state = self._state
        if state is None:
            self._location.configure(text="Weather")
            self._provider.configure(text="")
            self._temperature.configure(text="--°")
            self._condition.configure(text="Weather unavailable")
            self._details.configure(text="Waiting for a location and forecast")
            self._render_forecasts()
            return
        current = state.current
        self._location.configure(text=state.location_name or "Current Location")
        self._provider.configure(text=state.provider_label)
        self._temperature.configure(text=self._temperature_text(current.temperature_k))
        self._condition.configure(text=current.condition_label or "Unknown")
        self._details.configure(text="   •   ".join((
            f"Feels {self._temperature_text(current.apparent_temperature_k)}",
            f"Humidity {self._percent(current.relative_humidity)}",
            f"Wind {self._speed_text(current.wind_speed_m_s)}",
        )))
        self._render_forecasts()

    def _render_forecasts(self) -> None:
        for frame in (self._hourly, self._daily):
            for child in frame.winfo_children():
                child.destroy()
        state = self._state
        if state is None:
            return
        for column, item in enumerate(state.hourly[:6]):
            self._forecast_cell(
                self._hourly, column,
                item.timestamp.strftime("%I %p").lstrip("0"),
                self._temperature_text(item.temperature_k),
                item.condition_label,
            )
        for column, item in enumerate(state.daily[:6]):
            temps = f"{self._temperature_text(item.temperature_high_k)} / {self._temperature_text(item.temperature_low_k)}"
            self._forecast_cell(self._daily, column, item.date.strftime("%a"), temps, item.condition_label)

    def _forecast_cell(self, parent: tk.Frame, column: int, heading: str, value: str, detail: str) -> None:
        ui = self._theme_bundle().ui
        cell = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        cell.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 3, 3))
        parent.columnconfigure(column, weight=1, uniform="forecast")
        tk.Label(cell, text=heading, bg=ui.surface, fg=ui.text_muted, font=("Sans", 10, "bold")).pack(pady=(8, 2))
        tk.Label(cell, text=value, bg=ui.surface, fg=ui.text, font=("Sans", 15, "bold")).pack()
        tk.Label(cell, text=detail, bg=ui.surface, fg=ui.text_muted, font=("Sans", 9), wraplength=120).pack(padx=4, pady=(2, 8))

    def _temperature_text(self, value: float | None) -> str:
        if value is None:
            return "--°"
        if self._unit_system() is UnitSystem.IMPERIAL:
            return f"{kelvin_to_fahrenheit(value):.0f}°F"
        return f"{kelvin_to_celsius(value):.0f}°C"

    def _speed_text(self, value: float | None) -> str:
        if value is None:
            return "--"
        if self._unit_system() is UnitSystem.IMPERIAL:
            return f"{meters_per_second_to_miles_per_hour(value):.0f} mph"
        return f"{meters_per_second_to_kilometers_per_hour(value):.0f} km/h"

    @staticmethod
    def _percent(value: float | None) -> str:
        return "--" if value is None else f"{value * 100.0:.0f}%"
