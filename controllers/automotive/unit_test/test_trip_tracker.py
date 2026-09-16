# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for TripTracker."""

from datetime import datetime, timedelta, timezone

import pytest

from controllers.automotive import TripStatus
from controllers.automotive.trip_tracker import TripTracker
from controllers.automotive.vehicle_state import VehicleState
from controllers.navigation.navigation_state import GroundMotionState, PositionState


BASE = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)


def vehicle(
    seconds: float,
    speed_m_s: float | None,
    *,
    fuel_rate_m3_s: float | None = None,
    maf_kg_s: float | None = None,
    boost_pa: float | None = None,
) -> VehicleState:
    return VehicleState(
        timestamp=BASE + timedelta(seconds=seconds),
        vehicle_speed_m_s=speed_m_s,
        engine_fuel_rate_m3_s=fuel_rate_m3_s,
        mass_air_flow_kg_s=maf_kg_s,
        boost_pressure_pa=boost_pa,
    )


def motion(seconds: float, speed_m_s: float | None) -> GroundMotionState:
    return GroundMotionState(received_at=BASE + timedelta(seconds=seconds), speed_mps=speed_m_s)


def test_tracker_stays_idle_until_vehicle_moves() -> None:
    tracker = TripTracker()

    tracker.observe_vehicle_state(vehicle(0, 0.0))
    tracker.observe_vehicle_state(vehicle(5, 0.2))

    assert tracker.snapshot().status is TripStatus.IDLE
    assert tracker.snapshot().started_at is None


def test_tracker_starts_from_ground_motion_without_obd() -> None:
    tracker = TripTracker()

    tracker.observe_ground_motion_state(motion(0, 4.0))

    state = tracker.snapshot()
    assert state.status is TripStatus.ACTIVE
    assert state.started_at == BASE


def test_tracker_integrates_distance_time_and_speed() -> None:
    tracker = TripTracker()

    tracker.observe_ground_motion_state(motion(0, 10.0))
    tracker.observe_ground_motion_state(motion(10, 10.0))
    tracker.observe_ground_motion_state(motion(20, 20.0))

    state = tracker.snapshot()
    assert state.elapsed_s == pytest.approx(20.0)
    assert state.moving_s == pytest.approx(20.0)
    assert state.stopped_s == pytest.approx(0.0)
    assert state.distance_m == pytest.approx(250.0)
    assert state.average_speed_m_s == pytest.approx(12.5)
    assert state.maximum_speed_m_s == pytest.approx(20.0)


def test_tracker_marks_stationary_trip_paused_and_counts_stopped_time() -> None:
    tracker = TripTracker(pause_after_s=3.0)

    tracker.observe_ground_motion_state(motion(0, 5.0))
    tracker.observe_ground_motion_state(motion(10, 5.0))
    tracker.observe_ground_motion_state(motion(20, 0.0))
    tracker.observe_ground_motion_state(motion(24, 0.0))
    tracker.observe_ground_motion_state(motion(30, 0.0))

    state = tracker.snapshot()
    assert state.status is TripStatus.PAUSED
    assert state.elapsed_s == pytest.approx(30.0)
    assert state.moving_s == pytest.approx(20.0)
    assert state.stopped_s == pytest.approx(10.0)



def test_single_stationary_sample_does_not_pause_active_trip() -> None:
    tracker = TripTracker(pause_after_s=3.0)
    tracker.observe_ground_motion_state(motion(0, 5.0))
    tracker.observe_ground_motion_state(motion(1, 0.0))

    assert tracker.snapshot().status is TripStatus.ACTIVE


def test_motion_resumes_before_pause_dwell_expires() -> None:
    tracker = TripTracker(pause_after_s=3.0)
    tracker.observe_ground_motion_state(motion(0, 5.0))
    tracker.observe_ground_motion_state(motion(1, 0.0))
    tracker.observe_ground_motion_state(motion(2, 5.0))

    assert tracker.snapshot().status is TripStatus.ACTIVE


def test_tracker_integrates_direct_fuel_rate_and_calculates_consumption() -> None:
    tracker = TripTracker()

    tracker.observe_vehicle_state(vehicle(0, 10.0, fuel_rate_m3_s=2.0e-6))
    tracker.observe_vehicle_state(vehicle(10, 10.0, fuel_rate_m3_s=2.0e-6))

    state = tracker.snapshot()
    assert state.fuel_used_m3 == pytest.approx(2.0e-5)
    assert state.instantaneous_fuel_consumption_m3_per_m == pytest.approx(2.0e-7)
    assert state.average_fuel_consumption_m3_per_m == pytest.approx(2.0e-7)


def test_tracker_falls_back_to_maf_when_direct_fuel_rate_is_unavailable() -> None:
    tracker = TripTracker()

    tracker.observe_vehicle_state(vehicle(0, 10.0, maf_kg_s=0.0147))
    tracker.observe_vehicle_state(vehicle(10, 10.0, maf_kg_s=0.0147))

    state = tracker.snapshot()
    expected_flow = 0.0147 / 14.7 / 745.0
    assert state.fuel_used_m3 == pytest.approx(expected_flow * 10.0)
    assert state.instantaneous_fuel_consumption_m3_per_m == pytest.approx(
        expected_flow / 10.0
    )


def test_direct_fuel_rate_takes_priority_over_maf_fallback() -> None:
    tracker = TripTracker()

    tracker.observe_vehicle_state(
        vehicle(0, 10.0, fuel_rate_m3_s=3.0e-6, maf_kg_s=0.0147)
    )
    tracker.observe_vehicle_state(
        vehicle(10, 10.0, fuel_rate_m3_s=3.0e-6, maf_kg_s=0.0147)
    )

    assert tracker.snapshot().fuel_used_m3 == pytest.approx(3.0e-5)


def test_tracker_accumulates_boost_metrics() -> None:
    tracker = TripTracker(boost_threshold_pa=5000.0)

    tracker.observe_vehicle_state(
        vehicle(0, 10.0, fuel_rate_m3_s=2.0e-6, boost_pa=0.0)
    )
    tracker.observe_vehicle_state(
        vehicle(10, 10.0, fuel_rate_m3_s=4.0e-6, boost_pa=10000.0)
    )
    tracker.observe_vehicle_state(
        vehicle(20, 20.0, fuel_rate_m3_s=4.0e-6, boost_pa=12000.0)
    )

    state = tracker.snapshot()
    assert state.boost_time_s == pytest.approx(20.0)
    assert state.boost_distance_m == pytest.approx(250.0)
    assert state.boost_fuel_used_m3 == pytest.approx(7.0e-5)
    assert state.peak_boost_pa == pytest.approx(12000.0)


def test_tracker_ignores_small_positive_pressure_below_boost_threshold() -> None:
    tracker = TripTracker(boost_threshold_pa=5000.0)

    tracker.observe_vehicle_state(
        vehicle(0, 10.0, fuel_rate_m3_s=2.0e-6, boost_pa=2000.0)
    )
    tracker.observe_vehicle_state(
        vehicle(10, 10.0, fuel_rate_m3_s=2.0e-6, boost_pa=3000.0)
    )

    state = tracker.snapshot()
    assert state.boost_time_s == pytest.approx(0.0)
    assert state.boost_distance_m == pytest.approx(0.0)
    assert state.boost_fuel_used_m3 == pytest.approx(0.0)
    assert state.peak_boost_pa == pytest.approx(3000.0)

def test_tracker_captures_start_current_and_end_position() -> None:
    tracker = TripTracker()

    tracker.observe_position_state(
        PositionState(
            received_at=BASE,
            latitude_deg=42.80,
            longitude_deg=-83.01,
            fix_mode=3,
        )
    )
    tracker.observe_ground_motion_state(motion(1, 5.0))
    tracker.observe_position_state(
        PositionState(
            received_at=BASE + timedelta(seconds=20),
            latitude_deg=42.81,
            longitude_deg=-83.02,
            fix_mode=3,
        )
    )

    state = tracker.finish(BASE + timedelta(seconds=30))

    assert state.status is TripStatus.COMPLETE
    assert state.start_latitude_deg == pytest.approx(42.80)
    assert state.start_longitude_deg == pytest.approx(-83.01)
    assert state.current_latitude_deg == pytest.approx(42.81)
    assert state.current_longitude_deg == pytest.approx(-83.02)
    assert state.end_latitude_deg == pytest.approx(42.81)
    assert state.end_longitude_deg == pytest.approx(-83.02)
    assert state.ended_at == BASE + timedelta(seconds=30)


def test_reset_returns_tracker_to_idle() -> None:
    tracker = TripTracker()
    tracker.observe_vehicle_state(vehicle(0, 8.0))

    tracker.reset()

    assert tracker.snapshot().status is TripStatus.IDLE
    assert tracker.snapshot().distance_m == 0.0


def test_negative_motion_is_clamped_to_zero() -> None:
    tracker = TripTracker()
    tracker.observe_ground_motion_state(motion(0, 5.0))
    tracker.observe_ground_motion_state(motion(10, -3.0))

    state = tracker.snapshot()
    assert state.distance_m >= 0.0


def test_rejects_negative_moving_threshold() -> None:
    with pytest.raises(ValueError):
        TripTracker(moving_threshold_m_s=-0.1)


def test_rejects_negative_pause_delay() -> None:
    with pytest.raises(ValueError):
        TripTracker(pause_after_s=-0.1)
