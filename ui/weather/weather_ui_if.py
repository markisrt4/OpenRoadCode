# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Toolkit-independent weather UI contract using SI values."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class WeatherCurrentUiState:
    """Current weather values presented to a UI in SI units."""

    temperature_k: float | None = None
    apparent_temperature_k: float | None = None
    relative_humidity: float | None = None
    condition_label: str = ""
    precipitation_m: float | None = None
    pressure_pa: float | None = None
    wind_speed_m_s: float | None = None
    wind_direction_deg: float | None = None
    wind_gust_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherHourlyUiState:
    """One hourly weather presentation point using SI values."""

    timestamp: datetime
    temperature_k: float | None = None
    precipitation_probability: float | None = None
    condition_label: str = ""
    wind_speed_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherDailyUiState:
    """One daily weather presentation point using SI values."""

    date: date
    temperature_high_k: float | None = None
    temperature_low_k: float | None = None
    precipitation_probability: float | None = None
    condition_label: str = ""
    wind_speed_max_m_s: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherUiState:
    """Driver-facing weather state without toolkit or display-unit policy."""

    location_name: str = ""
    provider_label: str = ""
    fetched_at: float | None = None
    current: WeatherCurrentUiState = WeatherCurrentUiState()
    hourly: tuple[WeatherHourlyUiState, ...] = ()
    daily: tuple[WeatherDailyUiState, ...] = ()


class WeatherUiIf(ABC):
    """! @brief Receive driver-facing weather state in normalized SI units."""

    @abstractmethod
    def set_weather_state(self, state: WeatherUiState | None) -> None:
        """! @brief Display the latest weather state.

        @param state Latest SI-normalized UI state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_weather_request_handler(
        self,
        handler: "WeatherRequestHandlerIf | None",
    ) -> None:
        """! @brief Connect semantic weather requests.

        @param handler Weather request handler, or None to disconnect controls.
        """
        ...


from ui.weather.weather_request_handler_if import WeatherRequestHandlerIf
