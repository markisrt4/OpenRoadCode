# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""City forecast history, accumulations and explicit missing-data behavior."""

from unittest.mock import Mock

import pytest

from controllers.weather.city_weather import CityWeatherHours, CityWeatherProvider, WeatherCity, city_label, city_value

ANCHOR = 1791028800
CITY = WeatherCity("Detroit", 42.33, -83.05)


def series(missing=None, times=None):
    times = times or tuple(ANCHOR + h * 3600 for h in range(-24, 25))
    return CityWeatherHours(CITY, times, tuple(range(len(times))), (16.09344,) * len(times),
                            tuple(None if t == missing else 1.0 for t in times))


def test_temperature_and_wind_use_selected_hour_not_daily_summary():
    weather = series()
    assert city_value(weather, "temperature", 1, "past", ANCHOR) == 23
    assert city_value(weather, "temperature", 24, "past", ANCHOR) == 0
    assert city_value(weather, "temperature", 24, "future", ANCHOR) == 48
    assert city_label(city_value(weather, "wind", 1, "future", ANCHOR), "wind", True) == "10 mph"


def test_accumulation_counts_preceding_hours_and_never_crosses_window_boundary():
    weather = series()
    assert city_value(weather, "precipitation", 1, "past", ANCHOR) == 1
    assert city_value(weather, "precipitation", 24, "past", ANCHOR) == 24
    assert city_value(weather, "precipitation", 24, "future", ANCHOR) == 24
    # The past total includes the hour ending at the anchor. The future total excludes it.
    weather = series(missing=ANCHOR)
    assert city_value(weather, "precipitation", 1, "past", ANCHOR) is None
    assert city_value(weather, "precipitation", 24, "future", ANCHOR) == 24


def test_missing_hour_is_unavailable_not_zero_or_partial_accumulation():
    weather = series(missing=ANCHOR - 3600)
    assert city_value(weather, "precipitation", 24, "past", ANCHOR) is None
    assert city_value(weather, "precipitation", 1, "past", ANCHOR) == 1
    weather = series(times=(ANCHOR, ANCHOR + 3600))
    assert city_value(weather, "temperature", 24, "future", ANCHOR) is None
    assert city_value(weather, "precipitation", 2, "future", ANCHOR) is None
    assert city_label(None, "precipitation", True) == "—"
    assert city_label(0, "precipitation", True) == '0.00"'
    assert city_label(25.4, "precipitation", True) == '1.00"'
    assert city_label(0, "temperature", True) == "32°F"
    assert city_label(16.1, "wind", False) == "16 km/h"


@pytest.mark.parametrize('hours', [0, 25, True, 1.5])
def test_hour_range_is_enforced(hours):
    with pytest.raises(ValueError):
        city_value(series(), "temperature", hours, "past", ANCHOR)


def payload():
    return {"hourly_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h", "precipitation": "mm"},
            "hourly": {"time": [ANCHOR, ANCHOR + 3600], "temperature_2m": [10, None],
                       "wind_speed_10m": [float('nan'), 20], "precipitation": [0, -1]}}


def test_provider_batches_locations_with_history_and_forecasts_in_utc():
    session = Mock()
    session.get.return_value.json.return_value = [payload(), payload()]
    provider = CityWeatherProvider(session)
    cities = (CITY, WeatherCity("Flint", 43.01, -83.68))
    weather = provider.hourly(cities)
    assert tuple(item.city for item in weather) == cities
    assert weather[0].temperature_c == (10, None)
    assert weather[0].wind_kmh == (None, 20)
    assert weather[0].precipitation_mm == (0, None)
    params = session.get.call_args.kwargs["params"]
    assert params["latitude"] == '42.33,43.01'
    assert params["past_days"] == 2 and params["forecast_days"] == 3
    assert params["timezone"] == "UTC" and params["timeformat"] == "unixtime"
    assert "precipitation_probability" not in params["hourly"]
    session.get.assert_called_once()
    provider.close()
    session.close.assert_called_once()


@pytest.mark.parametrize('problem', ['units', 'times', 'locations'])
def test_provider_rejects_unusable_times_units_or_batch_mismatch(problem):
    data = payload()
    if problem == 'units':
        data['hourly_units']['temperature_2m'] = '°F'
    elif problem == 'times':
        data['hourly']['time'] = [ANCHOR, ANCHOR]
    session = Mock()
    session.get.return_value.json.return_value = [data, data] if problem == 'locations' else data
    with pytest.raises(ValueError):
        CityWeatherProvider(session).hourly((CITY,))
