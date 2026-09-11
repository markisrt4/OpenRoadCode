# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC trip presentation conversion."""

import pytest

from apps.orcUi.trip_presenter import TripPresenter
from messaging.contracts.automotive import TripStateData


def _data(**overrides):
    values = dict(
        status="active",
        started_at=None,
        ended_at=None,
        elapsed_s=3600.0,
        moving_s=3000.0,
        stopped_s=600.0,
        distance_m=1609.344,
        average_speed_m_s=10.0,
        maximum_speed_m_s=20.0,
        fuel_used_m3=None,
        instantaneous_fuel_consumption_m3_per_m=None,
        average_fuel_consumption_m3_per_m=None,
        estimated_range_m=None,
        boost_time_s=0.0,
        boost_distance_m=0.0,
        boost_fuel_used_m3=0.0,
        peak_boost_pa=None,
        start_latitude_deg=None,
        start_longitude_deg=None,
        current_latitude_deg=None,
        current_longitude_deg=None,
        end_latitude_deg=None,
        end_longitude_deg=None,
    )
    values.update(overrides)
    return TripStateData(**values)


def test_presenter_converts_distance_and_speed_to_imperial() -> None:
    state = TripPresenter.present(_data())

    assert state.distance_miles == pytest.approx(1.0)
    assert state.average_speed_mph == pytest.approx(22.369362920544)
    assert state.maximum_speed_mph == pytest.approx(44.738725841088)


def test_presenter_leaves_unavailable_fuel_metrics_empty() -> None:
    state = TripPresenter.present(_data())

    assert state.fuel_used_gallons is None
    assert state.economy_mpg is None
    assert state.estimated_range_miles is None


def test_presenter_converts_boost_metrics() -> None:
    state = TripPresenter.present(
        _data(
            fuel_used_m3=0.001,
            boost_time_s=120.0,
            boost_distance_m=1609.344,
            boost_fuel_used_m3=0.00025,
            peak_boost_pa=68947.57293168,
        )
    )

    assert state.boost_time_s == pytest.approx(120.0)
    assert state.boost_distance_miles == pytest.approx(1.0)
    assert state.boost_fuel_gallons == pytest.approx(
        0.00025 * 264.1720523581484
    )
    assert state.boost_fuel_percent == pytest.approx(25.0)
    assert state.peak_boost_psi == pytest.approx(10.0)
