# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Basic native Tk weather panel used by legacy carUi."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.weather import WeatherRequestHandlerIf, WeatherUiIf, WeatherUiState


class WeatherPanel(tk.Frame, WeatherUiIf):
    """Render a compact native weather summary while keeping values SI at the contract."""

    def __init__(self, parent: tk.Widget, *, on_noaa_radio_pressed: Callable[[], None]) -> None:
        super().__init__(parent)
        self._handler: WeatherRequestHandlerIf | None = None
        self._state: WeatherUiState | None = None

        header = tk.Frame(self)
        header.pack(fill="x", padx=16, pady=(12, 4))
        self._location = tk.Label(header, text="Weather", font=("TkDefaultFont", 18, "bold"))
        self._location.pack(side="left")
        tk.Button(header, text="Refresh", command=self._refresh).pack(side="right", padx=6)
        tk.Button(header, text="NOAA Radio", command=on_noaa_radio_pressed).pack(side="right", padx=6)

        self._current = tk.Label(self, text="Weather unavailable", font=("TkDefaultFont", 24, "bold"), anchor="w")
        self._current.pack(fill="x", padx=16, pady=8)
        self._details = tk.Label(self, text="", justify="left", anchor="nw")
        self._details.pack(fill="x", padx=16, pady=4)
        self._forecast = tk.Label(self, text="", justify="left", anchor="nw")
        self._forecast.pack(fill="both", expand=True, padx=16, pady=8)

    def set_weather_request_handler(self, handler: WeatherRequestHandlerIf | None) -> None:
        self._handler = handler

    def set_weather_state(self, state: WeatherUiState | None) -> None:
        self._state = state
        if state is None:
            self._current.configure(text="Weather unavailable")
            self._details.configure(text="")
            self._forecast.configure(text="")
            return

        self._location.configure(text=state.location_name or "Weather")
        current = state.current
        self._current.configure(text=f"{self._temperature_c(current.temperature_k)}  {current.condition_label}".strip())
        details = [
            f"Feels like {self._temperature_c(current.apparent_temperature_k)}",
            f"Humidity {self._percent(current.relative_humidity)}",
            f"Wind {self._speed_kmh(current.wind_speed_m_s)}",
            f"Provider {state.provider_label}",
        ]
        self._details.configure(text="   |   ".join(details))

        hourly = "   ".join(
            f"{item.timestamp:%-I %p} {self._temperature_c(item.temperature_k)} {item.condition_label}"
            for item in state.hourly[:5]
        )
        daily = "   ".join(
            f"{item.date:%a} {self._temperature_c(item.temperature_high_k)}/{self._temperature_c(item.temperature_low_k)} {item.condition_label}"
            for item in state.daily[:5]
        )
        self._forecast.configure(text=f"Hourly\n{hourly}\n\nDaily\n{daily}")

    def _refresh(self) -> None:
        if self._handler is not None:
            self._handler.request_refresh()

    @staticmethod
    def _temperature_c(value: float | None) -> str:
        return "--" if value is None else f"{value - 273.15:.0f}°C"

    @staticmethod
    def _percent(value: float | None) -> str:
        return "--" if value is None else f"{value * 100.0:.0f}%"

    @staticmethod
    def _speed_kmh(value: float | None) -> str:
        return "--" if value is None else f"{value * 3.6:.0f} km/h"
