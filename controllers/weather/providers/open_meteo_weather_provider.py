# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open-Meteo implementation of the weather provider contract."""

from __future__ import annotations

import time
from collections.abc import Callable

import requests

from common.units import (
    celsius_to_kelvin,
    hectopascals_to_pascals,
    kilometers_per_hour_to_meters_per_second,
    millimeters_to_meters,
    percent_to_ratio,
)
from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherCondition,
    WeatherLocation,
    WeatherSource,
    WeatherState,
)


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
            current=self._current_weather(forecast["current"]),
            hourly=self._hourly_forecast(forecast["hourly"]),
            daily=self._daily_forecast(forecast["daily"]),
        )

    @staticmethod
    def _condition(code: int | None) -> WeatherCondition:
        if code == 0:
            return WeatherCondition.CLEAR
        if code in (1, 2):
            return WeatherCondition.PARTLY_CLOUDY
        if code == 3:
            return WeatherCondition.CLOUDY
        if code in (45, 48):
            return WeatherCondition.FOG
        if code in (51, 53, 55, 56, 57):
            return WeatherCondition.DRIZZLE
        if code in (61, 63, 65, 80, 81, 82):
            return WeatherCondition.RAIN
        if code in (66, 67):
            return WeatherCondition.FREEZING_RAIN
        if code in (71, 73, 75, 77, 85, 86):
            return WeatherCondition.SNOW
        if code in (95, 96, 99):
            return WeatherCondition.THUNDERSTORM
        return WeatherCondition.UNKNOWN

    @classmethod
    def _current_weather(cls, data: dict) -> CurrentWeather:
        return CurrentWeather(
            temperature_k=celsius_to_kelvin(data.get("temperature_2m")),
            apparent_temperature_k=celsius_to_kelvin(data.get("apparent_temperature")),
            relative_humidity=percent_to_ratio(data.get("relative_humidity_2m")),
            condition=cls._condition(data.get("weather_code")),
            precipitation_m=millimeters_to_meters(data.get("precipitation")),
            rain_m=millimeters_to_meters(data.get("rain")),
            showers_m=millimeters_to_meters(data.get("showers")),
            snowfall_m=millimeters_to_meters(data.get("snowfall")),
            cloud_cover=percent_to_ratio(data.get("cloud_cover")),
            pressure_msl_pa=hectopascals_to_pascals(data.get("pressure_msl")),
            surface_pressure_pa=hectopascals_to_pascals(data.get("surface_pressure")),
            wind_speed_m_s=kilometers_per_hour_to_meters_per_second(data.get("wind_speed_10m")),
            wind_direction_deg=data.get("wind_direction_10m"),
            wind_gust_m_s=kilometers_per_hour_to_meters_per_second(data.get("wind_gusts_10m")),
        )

    @classmethod
    def _hourly_forecast(cls, data: dict) -> tuple[HourlyForecast, ...]:
        times = data.get("time", [])
        result = []
        for index, timestamp in enumerate(times):
            result.append(HourlyForecast(
                timestamp=__import__("datetime").datetime.fromisoformat(timestamp),
                temperature_k=celsius_to_kelvin(cls._at(data, "temperature_2m", index)),
                apparent_temperature_k=celsius_to_kelvin(cls._at(data, "apparent_temperature", index)),
                precipitation_probability=percent_to_ratio(cls._at(data, "precipitation_probability", index)),
                precipitation_m=millimeters_to_meters(cls._at(data, "precipitation", index)),
                condition=cls._condition(cls._at(data, "weather_code", index)),
                cloud_cover=percent_to_ratio(cls._at(data, "cloud_cover", index)),
                wind_speed_m_s=kilometers_per_hour_to_meters_per_second(cls._at(data, "wind_speed_10m", index)),
            ))
        return tuple(result)

    @classmethod
    def _daily_forecast(cls, data: dict) -> tuple[DailyForecast, ...]:
        from datetime import date, datetime
        result = []
        for index, day in enumerate(data.get("time", [])):
            sunrise = cls._at(data, "sunrise", index)
            sunset = cls._at(data, "sunset", index)
            result.append(DailyForecast(
                date=date.fromisoformat(day),
                condition=cls._condition(cls._at(data, "weather_code", index)),
                temperature_high_k=celsius_to_kelvin(cls._at(data, "temperature_2m_max", index)),
                temperature_low_k=celsius_to_kelvin(cls._at(data, "temperature_2m_min", index)),
                sunrise=datetime.fromisoformat(sunrise) if sunrise else None,
                sunset=datetime.fromisoformat(sunset) if sunset else None,
                precipitation_probability=percent_to_ratio(cls._at(data, "precipitation_probability_max", index)),
                wind_speed_max_m_s=kilometers_per_hour_to_meters_per_second(cls._at(data, "wind_speed_10m_max", index)),
            ))
        return tuple(result)

    @staticmethod
    def _at(data: dict, key: str, index: int):
        values = data.get(key, [])
        return values[index] if index < len(values) else None

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
