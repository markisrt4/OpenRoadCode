# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present normalized weather domain state through SI UI contracts."""

from __future__ import annotations

from controllers.weather.weather_state import WeatherState
from ui.weather import (
    WeatherCurrentUiState,
    WeatherDailyUiState,
    WeatherHourlyUiState,
    WeatherUiIf,
    WeatherUiState,
)


class WeatherPresenter:
    """Translate provider-neutral weather state into driver-facing SI UI state."""

    def __init__(self, weather_ui: WeatherUiIf) -> None:
        self._weather_ui = weather_ui

    def present(self, state: WeatherState) -> WeatherUiState:
        ui_state = self.to_ui_state(state)
        self._weather_ui.set_weather_state(ui_state)
        return ui_state

    @staticmethod
    def to_ui_state(state: WeatherState) -> WeatherUiState:
        current = state.current
        return WeatherUiState(
            location_name=state.location_name,
            provider_label=state.source.display_name,
            fetched_at=state.fetched_at,
            current=WeatherCurrentUiState(
                temperature_k=current.temperature_k,
                apparent_temperature_k=current.apparent_temperature_k,
                relative_humidity=current.relative_humidity,
                condition_label=WeatherPresenter._condition_label(current.condition.value),
                precipitation_m=current.precipitation_m,
                pressure_pa=current.pressure_msl_pa,
                wind_speed_m_s=current.wind_speed_m_s,
                wind_direction_deg=current.wind_direction_deg,
                wind_gust_m_s=current.wind_gust_m_s,
            ),
            hourly=tuple(
                WeatherHourlyUiState(
                    timestamp=item.timestamp,
                    temperature_k=item.temperature_k,
                    precipitation_probability=item.precipitation_probability,
                    condition_label=WeatherPresenter._condition_label(item.condition.value),
                    wind_speed_m_s=item.wind_speed_m_s,
                )
                for item in state.hourly
            ),
            daily=tuple(
                WeatherDailyUiState(
                    date=item.date,
                    temperature_high_k=item.temperature_high_k,
                    temperature_low_k=item.temperature_low_k,
                    precipitation_probability=item.precipitation_probability,
                    condition_label=WeatherPresenter._condition_label(item.condition.value),
                    wind_speed_max_m_s=item.wind_speed_max_m_s,
                )
                for item in state.daily
            ),
        )

    @staticmethod
    def _condition_label(value: str) -> str:
        return value.replace("_", " ").title()
