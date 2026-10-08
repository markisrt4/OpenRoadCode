# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Open-Meteo normalization into the ORC weather domain."""

import pytest

from controllers.weather.providers import OpenMeteoWeatherProvider
from controllers.weather.weather_state import WeatherCondition, WeatherLocation


@pytest.mark.parametrize(
    ("code", "condition"),
    [
        (0, WeatherCondition.CLEAR),
        (2, WeatherCondition.PARTLY_CLOUDY),
        (3, WeatherCondition.CLOUDY),
        (45, WeatherCondition.FOG),
        (53, WeatherCondition.DRIZZLE),
        (63, WeatherCondition.RAIN),
        (66, WeatherCondition.FREEZING_RAIN),
        (75, WeatherCondition.SNOW),
        (95, WeatherCondition.THUNDERSTORM),
        (None, WeatherCondition.UNKNOWN),
        (12345, WeatherCondition.UNKNOWN),
    ],
)
def test_wmo_codes_are_normalized(code, condition):
    assert OpenMeteoWeatherProvider._condition(code) is condition


def test_current_weather_is_normalized_to_si():
    current = OpenMeteoWeatherProvider._current_weather(
        {
            "temperature_2m": 19.3,
            "apparent_temperature": 20.2,
            "relative_humidity_2m": 84.0,
            "precipitation": 2.5,
            "rain": 2.0,
            "showers": 0.5,
            "snowfall": 0.0,
            "weather_code": 3,
            "cloud_cover": 75.0,
            "pressure_msl": 1013.25,
            "surface_pressure": 1000.0,
            "wind_speed_10m": 9.4,
            "wind_direction_10m": 270.0,
            "wind_gusts_10m": 18.0,
        }
    )

    assert current.temperature_k == pytest.approx(292.45)
    assert current.apparent_temperature_k == pytest.approx(293.35)
    assert current.relative_humidity == pytest.approx(0.84)
    assert current.precipitation_m == pytest.approx(0.0025)
    assert current.pressure_msl_pa == pytest.approx(101325.0)
    assert current.wind_speed_m_s == pytest.approx(9.4 / 3.6)
    assert current.wind_gust_m_s == pytest.approx(5.0)
    assert current.condition is WeatherCondition.CLOUDY


class _Response:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "current": {
                "temperature_2m": 10.0,
                "weather_code": 0,
            },
            "hourly": {
                "time": ["2026-09-16T19:00"],
                "temperature_2m": [10.0],
                "weather_code": [0],
            },
            "daily": {
                "time": ["2026-09-16"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "weather_code": [0],
            },
        }


class _Session:
    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return _Response()


def test_refresh_returns_typed_forecasts():
    session = _Session()
    provider = OpenMeteoWeatherProvider(session=session, clock=lambda: 123.0)
    state = provider.refresh(
        WeatherLocation(42.8028, -83.0127, "Romeo", "test")
    )

    assert state.fetched_at == 123.0
    assert state.current.condition is WeatherCondition.CLEAR
    assert state.current.temperature_k == pytest.approx(283.15)
    assert len(state.hourly) == 1
    assert state.hourly[0].temperature_k == pytest.approx(283.15)
    assert len(state.daily) == 1
    assert state.daily[0].temperature_high_k == pytest.approx(288.15)
