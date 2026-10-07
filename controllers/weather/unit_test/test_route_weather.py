# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Route sampling and hourly forecast selection regressions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from controllers.route_planning.route_planning_types import GeoPoint, RouteManeuver, RouteResult
from controllers.weather.route_weather import RouteWeatherProvider, sample_route


NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def route(maneuvers=()):
    return RouteResult(100, 7200, (GeoPoint(42, -84), GeoPoint(42, -83), GeoPoint(42, -82)), maneuvers)


def test_sampling_includes_origin_destination_and_bounds_requests():
    points = sample_route(route(), NOW)
    assert 2 <= len(points) <= 6
    assert points[0].point == route().shape[0]
    assert points[-1].point == route().shape[-1]
    assert points[0].arrival == NOW
    assert points[-1].arrival == NOW + timedelta(hours=2)
    assert all(a.distance_m < b.distance_m for a, b in zip(points, points[1:]))


def test_maneuver_time_changes_midpoint_eta():
    maneuvers = (RouteManeuver("First", None, 50, 5400, 0, 1),
                 RouteManeuver("Second", None, 50, 1800, 1, 2))
    points = sample_route(route(maneuvers), NOW, progress=0.5)
    assert points[0].point.longitude == pytest.approx(-83)
    assert points[-1].arrival == NOW + timedelta(minutes=30)


def test_remaining_route_uses_current_time_not_original_departure():
    points = sample_route(route(), NOW, progress=0.5)
    assert points[0].point.longitude == pytest.approx(-83)
    assert points[0].arrival == NOW
    assert points[-1].arrival == NOW + timedelta(hours=1)


def test_invalid_maneuver_coverage_falls_back_to_route_duration():
    points = sample_route(route((RouteManeuver("Bad", None, 50, 99999, 1, 2),)), NOW)
    assert points[-1].arrival == NOW + timedelta(hours=2)


def test_zero_length_route_is_one_checkpoint():
    point = GeoPoint(42, -83)
    assert len(sample_route(RouteResult(0, 0, (point, point), ()), NOW)) == 1


def test_dateline_interpolation_stays_near_dateline():
    points = sample_route(RouteResult(100, 3600, (GeoPoint(40, 179), GeoPoint(40, -179)), ()), NOW)
    assert all(abs(p.point.longitude) >= 179 for p in points)


@pytest.mark.parametrize("duration", [-1, float("nan"), float("inf")])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(ValueError):
        sample_route(RouteResult(10, duration, (GeoPoint(42, -83),), ()), NOW)


def hourly(temperature=10):
    return {"hourly": {"time": [NOW.timestamp() + i * 3600 for i in range(4)],
                       "temperature_2m": [temperature] * 4,
                       "precipitation_probability": [0, 20, 40, 60],
                       "wind_speed_10m": [15] * 4, "weather_code": [71] * 4}}


def test_batch_uses_utc_and_selects_arrival_hour():
    session = Mock()
    points = sample_route(route(), NOW)
    session.get.return_value.json.return_value = [hourly(i) for i in range(len(points))]
    result = RouteWeatherProvider(session).forecast(points)
    params = session.get.call_args.kwargs["params"]
    assert params["timezone"] == "UTC"
    assert params["timeformat"] == "unixtime"
    assert len(params["latitude"].split(",")) == len(points)
    session.get.assert_called_once()
    assert result[-1].rain_probability == 40
    assert result[-1].condition == "snow"
    assert result[-1].temperature_c == len(points) - 1


def test_null_and_nonfinite_values_remain_unavailable_not_zero():
    session = Mock()
    payload = hourly()
    payload["hourly"]["temperature_2m"] = [None] * 4
    payload["hourly"]["wind_speed_10m"] = [float("nan")] * 4
    payload["hourly"]["precipitation_probability"] = [101] * 4
    session.get.return_value.json.return_value = payload
    point = sample_route(RouteResult(0, 0, (GeoPoint(42, -83),), ()), NOW)
    result = RouteWeatherProvider(session).forecast(point)[0]
    assert result.temperature_c is None
    assert result.wind_kmh is None
    assert result.rain_probability is None


@pytest.mark.parametrize("payload", [{}, [], {"hourly": {"time": [NOW.timestamp() - 7200]}}])
def test_incomplete_or_out_of_range_forecasts_fail(payload):
    session = Mock()
    session.get.return_value.json.return_value = payload
    points = sample_route(RouteResult(0, 0, (GeoPoint(42, -83),), ()), NOW)
    with pytest.raises(ValueError):
        RouteWeatherProvider(session).forecast(points)
