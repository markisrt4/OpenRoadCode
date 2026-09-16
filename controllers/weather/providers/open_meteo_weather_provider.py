# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open-Meteo implementation of the weather provider contract."""

from __future__ import annotations

import time
from collections.abc import Callable

import requests

from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import WeatherLocation, WeatherSource, WeatherState


class OpenMeteoWeatherProvider(WeatherProviderIf):
    URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._clock = clock

    @property
    def provider_id(self) -> str:
        return "open_meteo"

    def refresh(self, location: WeatherLocation | None = None) -> WeatherState:
        if location is None:
            raise ValueError("Open-Meteo requires a weather location")
        response = self._session.get(
            self.URL,
            params=self._request_params(location),
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        forecast = response.json()
        if not isinstance(forecast, dict) or not all(
            key in forecast for key in ("current", "hourly", "daily")
        ):
            raise ValueError("Open-Meteo returned incomplete forecast data")
        return WeatherState(
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.name,
            location_source=location.source,
            source=WeatherSource("open_meteo", "Open-Meteo"),
            fetched_at=self._clock(),
            current=forecast["current"],
            hourly=forecast["hourly"],
            daily=forecast["daily"],
        )

    @staticmethod
    def _request_params(location: WeatherLocation) -> dict[str, str | float | int]:
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": "auto",
            "current": ",".join((
                "temperature_2m", "apparent_temperature",
                "relative_humidity_2m", "precipitation", "rain", "showers",
                "snowfall", "weather_code", "cloud_cover", "pressure_msl",
                "surface_pressure", "wind_speed_10m", "wind_direction_10m",
                "wind_gusts_10m",
            )),
            "hourly": ",".join((
                "temperature_2m", "apparent_temperature",
                "precipitation_probability", "precipitation",
                "weather_code", "cloud_cover", "wind_speed_10m",
            )),
            "daily": ",".join((
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "sunrise", "sunset", "precipitation_probability_max",
                "wind_speed_10m_max",
            )),
            "forecast_days": 7,
        }
