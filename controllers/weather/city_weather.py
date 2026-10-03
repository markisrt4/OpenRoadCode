# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hourly city weather for a television-style map, using UTC throughout."""

from dataclasses import dataclass
import math

import requests

from controllers.weather.providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


@dataclass(frozen=True)
class WeatherCity:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CityWeatherHours:
    city: WeatherCity
    times: tuple[int, ...]
    temperature_c: tuple[float | None, ...]
    wind_kmh: tuple[float | None, ...]
    precipitation_mm: tuple[float | None, ...]


def city_value(weather: CityWeatherHours, kind: str, hours: int, period: str, anchor: int) -> float | None:
    """Select an hourly snapshot or a complete rainfall total over 1–24 hours.

    Precipitation at time T is the amount in the preceding hour. Any missing
    hour makes a total unavailable, rather than quietly becoming zero rain.
    """
    if kind not in {"temperature", "wind", "precipitation"} or period not in {"past", "future"}:
        raise ValueError("Unknown city weather view")
    if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 24:
        raise ValueError("City weather hours must be between 1 and 24")
    lookup = {time: index for index, time in enumerate(weather.times)}
    if kind == "precipitation":
        end = anchor if period == "past" else anchor + hours * 3600
        selected = range(end - (hours - 1) * 3600, end + 1, 3600)
        values = [weather.precipitation_mm[lookup[t]] if t in lookup else None for t in selected]
        return sum(values) if all(value is not None for value in values) else None
    target = anchor + hours * 3600 * (-1 if period == "past" else 1)
    index = lookup.get(target)
    if index is None:
        return None
    return (weather.temperature_c if kind == "temperature" else weather.wind_kmh)[index]


def city_label(value: float | None, kind: str, imperial: bool) -> str:
    """Format a map number in the user's units without treating missing data as zero."""
    if value is None:
        return "—"
    if kind == "temperature":
        return f"{value * 9 / 5 + 32:.0f}°F" if imperial else f"{value:.0f}°C"
    if kind == "wind":
        return f"{value / 1.609344:.0f} mph" if imperial else f"{value:.0f} km/h"
    return f'{value / 25.4:.2f}"' if imperial else f"{value:.1f} mm"


class CityWeatherProvider:
    """Fetch recent model estimates and future hourly forecasts in one batch."""

    def __init__(self, session=None):
        self._session = session or requests.Session()

    def close(self):
        """Release the HTTP connection pool."""
        self._session.close()

    def hourly(self, cities: tuple[WeatherCity, ...]) -> tuple[CityWeatherHours, ...]:
        """Return matching Celsius/km/h/mm time series for up to twelve map cities."""
        if not cities:
            return ()
        if len(cities) > 12 or any(not city.name or not math.isfinite(city.latitude)
                                  or not math.isfinite(city.longitude) or not -90 <= city.latitude <= 90
                                  or not -180 <= city.longitude <= 180 for city in cities):
            raise ValueError("City weather requires up to twelve valid named locations")
        response = self._session.get(OpenMeteoWeatherProvider.URL, params={
            "latitude": ",".join(str(city.latitude) for city in cities),
            "longitude": ",".join(str(city.longitude) for city in cities),
            "hourly": "temperature_2m,wind_speed_10m,precipitation",
            "past_days": 2, "forecast_days": 3, "timezone": "UTC", "timeformat": "unixtime",
            "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
        }, timeout=20)
        response.raise_for_status()
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(cities):
            raise ValueError("City weather returned an unexpected number of locations")
        results = []
        for city, location in zip(cities, locations):
            hourly = location.get("hourly", {})
            times = hourly.get("time", [])
            if (not times or any(not isinstance(t, int) or isinstance(t, bool) for t in times)
                    or any(b <= a for a, b in zip(times, times[1:]))):
                raise ValueError("City weather has no usable ordered hourly timestamps")
            units = location.get("hourly_units", {})
            for key, unit in (("temperature_2m", "°C"), ("wind_speed_10m", "km/h"), ("precipitation", "mm")):
                if units.get(key) != unit:
                    raise ValueError(f"City weather returned unexpected {key} units")

            def values(key, low, high):
                raw = hourly.get(key, [])
                return tuple(item if isinstance(item, (int, float)) and not isinstance(item, bool)
                             and math.isfinite(item) and low <= item <= high else None
                             for item in (raw[i] if i < len(raw) else None for i in range(len(times))))

            results.append(CityWeatherHours(city, tuple(times), values("temperature_2m", -100, 70),
                                             values("wind_speed_10m", 0, 500), values("precipitation", 0, 1000)))
        return tuple(results)
