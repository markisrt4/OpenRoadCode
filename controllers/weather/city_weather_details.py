# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Convert cached city hours into immutable detail presentation."""
from datetime import datetime, timezone

from controllers.weather.city_weather import city_value
from ui.weather.weather_overlay_state import CityWeatherDetails, CityWeatherHour


def city_identity(city):
    """Keep selection stable across viewport ordering and duplicate city names."""
    return f"weather-city:{city.name}:{city.latitude:.5f}:{city.longitude:.5f}"


def city_details(weather, period, hours, anchor, fetched_at):
    """Use the selected overlay window and its already downloaded hourly values."""
    def utc(stamp):
        return datetime.fromtimestamp(stamp, timezone.utc)

    def convert(value, kind):
        if value is None:
            return None
        return value + 273.15 if kind == 'temperature' else value / 3.6 if kind == 'wind' else value / 1000

    target = anchor + hours * 3600 * (-1 if period == 'past' else 1)
    start, end = (anchor - 24 * 3600, anchor) if period == 'past' else (anchor + 3600, anchor + 24 * 3600)
    rows = tuple(CityWeatherHour(utc(stamp), convert(weather.temperature_c[index], 'temperature'),
                               convert(weather.wind_kmh[index], 'wind'),
                               convert(weather.precipitation_mm[index], 'precipitation'))
                 for index, stamp in enumerate(weather.times) if start <= stamp <= end)
    # Temperature/wind are snapshots; precipitation summarizes the selected window.
    return CityWeatherDetails(city_identity(weather.city), weather.city.name, utc(target),
                              *(convert(city_value(weather, kind, hours, period, anchor), kind)
                                for kind in ('temperature', 'wind', 'precipitation')),
                              rows, utc(fetched_at))
