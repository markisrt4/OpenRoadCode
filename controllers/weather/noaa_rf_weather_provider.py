# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Read NOAA RF forecast snapshots through the normalized weather contract."""

from __future__ import annotations

from collections.abc import Callable
from time import time

from controllers.weather.noaa_forecast_store import NoaaForecastStore
from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import (
    CurrentWeather,
    TextForecastPeriod,
    WeatherLocation,
    WeatherSource,
    WeatherState,
)


class NoaaRfWeatherProvider(WeatherProviderIf):
    """Provide geographically verified NOAA text forecasts without RF dependencies."""

    def __init__(
        self,
        store: NoaaForecastStore,
        *,
        area_matches: Callable[[str, WeatherLocation], bool],
        max_reception_age_seconds: float = 3600.0,
        clock: Callable[[], float] = time,
    ) -> None:
        if max_reception_age_seconds <= 0:
            raise ValueError("max_reception_age_seconds must be positive")
        self._store = store
        self._area_matches = area_matches
        self._max_age = max_reception_age_seconds
        self._clock = clock

    @property
    def provider_id(self) -> str:
        """Return the stable NOAA RF source identifier."""
        return "noaa_rf"

    def refresh(self, location: WeatherLocation) -> WeatherState:
        """Return a matched recent RF forecast or refuse to claim locality."""
        snapshot = self._store.latest()
        if snapshot is None:
            raise RuntimeError("No NOAA RF forecast received")
        if not snapshot.area or not self._area_matches(snapshot.area, location):
            raise RuntimeError("NOAA RF forecast area is unverified for this location")
        age = self._clock() - snapshot.received_at
        if age < 0 or age > self._max_age:
            raise RuntimeError("NOAA RF forecast reception is stale")
        if snapshot.boundary_suspected:
            raise RuntimeError("NOAA RF forecast cycle boundary is uncertain")

        def fahrenheit_to_kelvin(value: float | None) -> float | None:
            return None if value is None else (value - 32.0) * 5.0 / 9.0 + 273.15

        period = TextForecastPeriod(
            label=snapshot.period,
            conditions=snapshot.conditions,
            temperature_high_k=fahrenheit_to_kelvin(snapshot.high_f),
            temperature_low_k=fahrenheit_to_kelvin(snapshot.low_f),
            precipitation_probability=(
                None if snapshot.precipitation_chance_percent is None
                else snapshot.precipitation_chance_percent / 100.0
            ),
        )
        return WeatherState(
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.name,
            location_source=location.source,
            source=WeatherSource(provider_id=self.provider_id, display_name="NOAA Weather Radio"),
            fetched_at=snapshot.received_at,
            current=CurrentWeather(),
            text_periods=(period,),
        )
