# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-friendly native Tk weather dashboard for orcUi."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import tkinter as tk

from common.units import (
    UnitSystem,
    kelvin_to_celsius,
    kelvin_to_fahrenheit,
    meters_per_second_to_kilometers_per_hour,
    meters_per_second_to_miles_per_hour,
    pascals_to_kilopascals,
)
from ui.theme import ThemeBundle
from ui.weather import WeatherRequestHandlerIf, WeatherUiIf, WeatherUiState


def weather_symbol(condition: str, *, nighttime: bool = False) -> str:
    """Return a compact Unicode symbol for a normalized condition label."""
    text = condition.lower()
    if "thunder" in text:
        return "⚡"
    if "snow" in text or "sleet" in text:
        return "❄"
    if "rain" in text or "drizzle" in text or "shower" in text:
        return "☂"
    if "fog" in text or "mist" in text:
        return "≋"
    if "clear" in text or "sun" in text:
        return "☾" if nighttime else "☀"
    if "partly" in text:
        return "☾☁" if nighttime else "☀☁"
    if "cloud" in text or "overcast" in text:
        return "☁"
    return "◌"


class OrcWeatherPanel(tk.Frame, WeatherUiIf):
    """Render weather as a glanceable, touch-friendly automotive dashboard."""

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
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._header = tk.Frame(self, bg=ui.background)
        self._header.grid(row=0, column=0, sticky="ew", padx=22, pady=(12, 7))
        self._header.grid_columnconfigure(0, weight=1)
        self._location = tk.Label(
            self._header, text="WEATHER", anchor="w", font=("Sans", 13, "bold")
        )
        self._location.grid(row=0, column=0, sticky="w")
        self._provider = tk.Label(
            self._header, text="", anchor="w", font=("Sans", 9)
        )
        self._provider.grid(row=1, column=0, sticky="w", pady=(1, 0))
        self._weather_radio = tk.Button(
            self._header,
            text="◉  NOAA",
            command=self._request_weather_radio,
            padx=12,
            pady=6,
            font=("Sans", 9, "bold"),
        )
        self._weather_radio.grid(row=0, column=1, rowspan=2, padx=(8, 6))
        self._refresh = tk.Button(
            self._header,
            text="↻  REFRESH",
            command=self._request_refresh,
            padx=12,
            pady=6,
            font=("Sans", 9, "bold"),
        )
        self._refresh.grid(row=0, column=2, rowspan=2)

        self._hero = tk.Frame(self, bd=0, highlightthickness=1)
        self._hero.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 9))
        self._hero.grid_columnconfigure(2, weight=1)

        self._symbol = tk.Label(
            self._hero, text="◌", width=3, font=("Sans", 46), anchor="center"
        )
        self._symbol.grid(row=0, column=0, rowspan=2, padx=(16, 4), pady=10)
        self._temperature = tk.Label(
            self._hero, text="--°", font=("Sans", 48, "bold"), anchor="w"
        )
        self._temperature.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 20), pady=8)

        self._condition = tk.Label(
            self._hero, text="Weather unavailable", font=("Sans", 20, "bold"), anchor="w"
        )
        self._condition.grid(row=0, column=2, sticky="sw", pady=(12, 1))
        self._summary = tk.Label(
            self._hero, text="Waiting for location and forecast", font=("Sans", 10), anchor="w"
        )
        self._summary.grid(row=1, column=2, sticky="nw", pady=(1, 12))

        self._metrics = tk.Frame(self._hero)
        self._metrics.grid(row=0, column=3, rowspan=2, sticky="nsew", padx=(12, 14), pady=10)
        self._metric_cards: list[tuple[tk.Frame, tk.Label, tk.Label]] = []
        for column, heading in enumerate(("HUMIDITY", "WIND", "PRESSURE")):
            card = tk.Frame(self._metrics, bd=0, highlightthickness=1)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 4, 0))
            self._metrics.grid_columnconfigure(column, weight=1, uniform="metric")
            title = tk.Label(card, text=heading, font=("Sans", 8, "bold"))
            title.pack(padx=10, pady=(7, 1))
            value = tk.Label(card, text="--", font=("Sans", 11, "bold"))
            value.pack(padx=10, pady=(0, 7))
            self._metric_cards.append((card, title, value))

        self._forecast_area = tk.Frame(self)
        self._forecast_area.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 10))
        self._forecast_area.grid_columnconfigure(0, weight=1)
        self._forecast_area.grid_rowconfigure(1, weight=1)
        self._forecast_area.grid_rowconfigure(3, weight=1)

        self._hourly_title = self._section_title(self._forecast_area, "HOURLY")
        self._hourly_title.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._hourly = tk.Frame(self._forecast_area)
        self._hourly.grid(row=1, column=0, sticky="nsew")

        self._daily_title = self._section_title(self._forecast_area, "6-DAY FORECAST")
        self._daily_title.grid(row=2, column=0, sticky="ew", pady=(9, 4))
        self._daily = tk.Frame(self._forecast_area)
        self._daily.grid(row=3, column=0, sticky="nsew")

        self.set_theme_bundle(theme_bundle())

    @staticmethod
    def _section_title(parent: tk.Misc, text: str) -> tk.Label:
        return tk.Label(parent, text=text, font=("Sans", 9, "bold"), anchor="w")

    def set_weather_request_handler(
        self, handler: WeatherRequestHandlerIf | None
    ) -> None:
        self._handler = handler

    def set_weather_state(self, state: WeatherUiState | None) -> None:
        self._state = state
        self._render()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        ui = theme.ui
        self.configure(bg=ui.background)
        for frame in (self._header, self._forecast_area, self._hourly, self._daily):
            frame.configure(bg=ui.background)
        self._location.configure(bg=ui.background, fg=ui.text)
        self._provider.configure(bg=ui.background, fg=ui.text_muted)
        for button in (self._refresh, self._weather_radio):
            button.configure(
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground=ui.text,
                relief=tk.FLAT,
                bd=0,
            )

        self._hero.configure(bg=ui.surface, highlightbackground=ui.border)
        for widget in (self._symbol, self._temperature, self._condition, self._summary):
            widget.configure(bg=ui.surface)
        self._symbol.configure(fg=ui.accent_primary)
        self._temperature.configure(fg=ui.text)
        self._condition.configure(fg=ui.text)
        self._summary.configure(fg=ui.text_muted)
        self._metrics.configure(bg=ui.surface)

        for card, title, value in self._metric_cards:
            card.configure(bg=ui.surface_alt, highlightbackground=ui.border)
            title.configure(bg=ui.surface_alt, fg=ui.text_muted)
            value.configure(bg=ui.surface_alt, fg=ui.text)

        for title in (self._hourly_title, self._daily_title):
            title.configure(bg=ui.background, fg=ui.text_muted)
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
            self._location.configure(text="WEATHER")
            self._provider.configure(text="")
            self._symbol.configure(text="◌")
            self._temperature.configure(text="--°")
            self._condition.configure(text="Weather unavailable")
            self._summary.configure(text="Waiting for location and forecast")
            for _, _, value in self._metric_cards:
                value.configure(text="--")
            self._render_forecasts()
            return

        current = state.current
        location = state.location_name.strip()
        self._location.configure(
            text="WEATHER" if not location or location.lower() == "configured fallback" else location
        )
        self._provider.configure(text=self._provider_text(state))
        self._symbol.configure(text=weather_symbol(current.condition_label))
        self._temperature.configure(text=self._temperature_text(current.temperature_k))
        self._condition.configure(text=current.condition_label or "Unknown")
        self._summary.configure(
            text=(
                f"Feels like {self._temperature_text(current.apparent_temperature_k)}"
                f"   •   Gusts {self._speed_text(current.wind_gust_m_s)}"
                f"   •   {self._direction_text(current.wind_direction_deg)}"
            )
        )
        self._metric_cards[0][2].configure(text=self._percent(current.relative_humidity))
        self._metric_cards[1][2].configure(text=self._speed_text(current.wind_speed_m_s))
        self._metric_cards[2][2].configure(text=self._pressure_text(current.pressure_pa))
        self._render_forecasts()

    def _provider_text(self, state: WeatherUiState) -> str:
        label = state.provider_label or "Weather"
        if state.fetched_at is None:
            return label
        updated = datetime.fromtimestamp(state.fetched_at).strftime("%I:%M %p").lstrip("0")
        return f"{label}  •  Updated {updated}"

    def _render_forecasts(self) -> None:
        for frame in (self._hourly, self._daily):
            for child in frame.winfo_children():
                child.destroy()
        state = self._state
        if state is None:
            return

        now = datetime.now().astimezone()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        upcoming = [
            item for item in state.hourly
            if self._local_timestamp(item.timestamp) >= current_hour
        ]
        for column, item in enumerate(upcoming[:6]):
            precipitation = (
                "" if item.precipitation_probability is None
                else f"☂ {self._percent(item.precipitation_probability)}"
            )
            self._forecast_cell(
                self._hourly,
                column,
                self._local_timestamp(item.timestamp).strftime("%I %p").lstrip("0"),
                weather_symbol(
                    item.condition_label,
                    nighttime=self._is_night(self._local_timestamp(item.timestamp)),
                ),
                self._temperature_text(item.temperature_k),
                item.condition_label,
                precipitation,
            )

        for column, item in enumerate(state.daily[:6]):
            precipitation = (
                "" if item.precipitation_probability is None
                else f"☂ {self._percent(item.precipitation_probability)}"
            )
            temperatures = (
                f"{self._temperature_text(item.temperature_high_k)}  "
                f"{self._temperature_text(item.temperature_low_k)}"
            )
            self._forecast_cell(
                self._daily,
                column,
                item.date.strftime("%a").upper(),
                weather_symbol(item.condition_label),
                temperatures,
                item.condition_label,
                precipitation,
            )

    def _forecast_cell(
        self,
        parent: tk.Frame,
        column: int,
        heading: str,
        symbol: str,
        value: str,
        detail: str,
        footer: str,
    ) -> None:
        ui = self._theme_bundle().ui
        cell = tk.Frame(
            parent, bg=ui.surface, bd=0, highlightthickness=1, highlightbackground=ui.border
        )
        cell.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 3, 3),
        )
        parent.grid_columnconfigure(column, weight=1, uniform="forecast")
        parent.grid_rowconfigure(0, weight=1)

        tk.Label(
            cell, text=heading, bg=ui.surface, fg=ui.text_muted, font=("Sans", 8, "bold")
        ).pack(pady=(6, 0))
        tk.Label(
            cell, text=symbol, bg=ui.surface, fg=ui.accent_primary, font=("Sans", 22)
        ).pack(pady=(0, 0))
        tk.Label(
            cell, text=value, bg=ui.surface, fg=ui.text, font=("Sans", 13, "bold")
        ).pack()
        tk.Label(
            cell,
            text=detail,
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 7),
            wraplength=92,
            height=2,
        ).pack(padx=3, pady=(1, 0))
        tk.Label(
            cell, text=footer, bg=ui.surface, fg=ui.accent_primary, font=("Sans", 8, "bold")
        ).pack(pady=(1, 6))

    @staticmethod
    def _local_timestamp(value: datetime) -> datetime:
        return value.astimezone()

    @staticmethod
    def _is_night(value: datetime) -> bool:
        return value.hour < 6 or value.hour >= 20

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

    def _pressure_text(self, value: float | None) -> str:
        if value is None:
            return "--"
        kpa = pascals_to_kilopascals(value)
        if self._unit_system() is UnitSystem.IMPERIAL:
            return f"{kpa * 0.2952998751:.2f} inHg"
        return f"{kpa:.1f} kPa"

    @staticmethod
    def _percent(value: float | None) -> str:
        return "--" if value is None else f"{value * 100.0:.0f}%"

    @staticmethod
    def _direction_text(value: float | None) -> str:
        if value is None:
            return "--"
        names = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        return f"{names[int((value + 22.5) % 360 // 45)]} {value:.0f}°"
