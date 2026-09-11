# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the automotive trip domain contract."""

from datetime import datetime, timezone

import pytest

from controllers.automotive import TripIf, TripState, TripStatus


def test_trip_state_defaults_to_idle_zeroed_snapshot() -> None:
    state = TripState()

    assert state.status is TripStatus.IDLE
    assert state.started_at is None
    assert state.ended_at is None
    assert state.elapsed_s == 0.0
    assert state.moving_s == 0.0
    assert state.stopped_s == 0.0
    assert state.distance_m == 0.0
    assert state.average_speed_m_s is None
    assert state.maximum_speed_m_s is None
    assert state.fuel_used_m3 is None


def test_trip_state_preserves_complete_snapshot_values() -> None:
    started = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    ended = datetime(2026, 9, 10, 12, 30, tzinfo=timezone.utc)

    state = TripState(
        status=TripStatus.COMPLETE,
        started_at=started,
        ended_at=ended,
        elapsed_s=1800.0,
        moving_s=1500.0,
        stopped_s=300.0,
        distance_m=20_000.0,
        average_speed_m_s=20_000.0 / 1500.0,
        maximum_speed_m_s=31.0,
    )

    assert state.status is TripStatus.COMPLETE
    assert state.started_at is started
    assert state.ended_at is ended
    assert state.distance_m == 20_000.0
    assert state.moving_s + state.stopped_s == pytest.approx(state.elapsed_s)


def test_trip_if_is_abstract() -> None:
    with pytest.raises(TypeError):
        TripIf()
