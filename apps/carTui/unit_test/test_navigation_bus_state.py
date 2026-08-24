# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for the Car TUI navigation telemetry cache."""

import math
from datetime import datetime, timezone

import pytest

from apps.carTui.navigation_bus_state import NavigationBusState
from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import (
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
    encode_position_state,
)
from messaging.contracts.navigation.attitude_state_codec import encode_attitude_state
from messaging.contracts.navigation.imu_state_codec import encode_imu_state
from messaging.contracts.navigation.motion_state_codec import encode_motion_state


TIMESTAMP = {"seconds": 10, "nanoseconds": 0}


def test_waits_until_both_attitude_and_imu_arrive():
    state = NavigationBusState()
    initial = state.snapshot()
    assert not initial.connected
    assert initial.status == "Waiting for navigation telemetry"

    state.set_attitude(decode_attitude_state(encode_attitude_state(
        timestamp=TIMESTAMP,
        source="test-navigation",
        heading_rad=math.pi / 2,
        pitch_rad=math.pi / 12,
        roll_rad=-math.pi / 6,
    )))
    assert not state.snapshot().connected

    state.set_imu(decode_imu_state(encode_imu_state(
        timestamp=TIMESTAMP,
        source="test-navigation",
        acceleration_m_s2={"x": 1.0, "y": 2.0, "z": 9.8},
        linear_acceleration_m_s2={"x": 1.0, "y": 2.0, "z": 0.0},
        angular_velocity_rad_s={"x": 0.01, "y": 0.02, "z": 0.03},
    )))

    snapshot = state.snapshot()
    assert snapshot.connected
    assert snapshot.heading_deg == pytest.approx(90.0)
    assert snapshot.pitch_deg == pytest.approx(15.0)
    assert snapshot.roll_deg == pytest.approx(-30.0)
    assert snapshot.linear_acceleration_mps2.y == pytest.approx(2.0)
    assert snapshot.angular_velocity_rad_s.z == pytest.approx(0.03)
    assert snapshot.attitude_count == 1
    assert snapshot.imu_count == 1


def test_position_and_motion_messages_populate_navigation_snapshot():
    state = NavigationBusState()
    position = PositionState(
        received_at=datetime.fromtimestamp(10, tz=timezone.utc),
        latitude_deg=42.8028,
        longitude_deg=-83.0127,
        altitude_m=201.5,
        speed_mps=12.5,
        course_deg=87.0,
        fix_mode=3,
        satellites_visible=12,
        satellites_used=9,
        accuracy_m=2.4,
        source="test-gps",
    )
    state.set_position(decode_position_state(encode_position_state(position)))
    state.set_motion(decode_motion_state(encode_motion_state(
        timestamp=TIMESTAMP,
        source="test-motion",
        heading_rad=math.radians(88.0),
        ground_speed_m_s=12.6,
        vertical_speed_m_s=0.4,
        turn_rate_rad_s=0.03,
    )))

    snapshot = state.snapshot()
    assert snapshot.gps is not None
    assert snapshot.gps.has_fix
    assert snapshot.gps.latitude_deg == pytest.approx(42.8028)
    assert snapshot.gps.longitude_deg == pytest.approx(-83.0127)
    assert snapshot.gps.speed_mps == pytest.approx(12.5)
    assert snapshot.gps.course_deg == pytest.approx(87.0)
    assert snapshot.gps.satellites_used == 9
    assert snapshot.ground_speed_m_s == pytest.approx(12.6)
    assert snapshot.vertical_speed_m_s == pytest.approx(0.4)
    assert snapshot.turn_rate_rad_s == pytest.approx(0.03)
    assert snapshot.position_count == 1
    assert snapshot.motion_count == 1


def test_error_disconnects_until_next_good_message():
    state = NavigationBusState()
    state.set_error("openroad.navigation.imu", RuntimeError("bad sample"))
    assert not state.snapshot().connected
    assert "bad sample" in state.snapshot().status
