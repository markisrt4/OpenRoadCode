# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for the Car TUI navigation telemetry cache."""

import math

import pytest

from apps.carTui.navigation_bus_state import NavigationBusState
from messaging.contracts.navigation import decode_attitude_state, decode_imu_state
from messaging.contracts.navigation.attitude_state_codec import encode_attitude_state
from messaging.contracts.navigation.imu_state_codec import encode_imu_state
from messaging.contracts.common import Timestamp


def test_waits_until_both_attitude_and_imu_arrive():
    state = NavigationBusState()
    initial = state.snapshot()
    assert not initial.connected
    assert initial.status == "Waiting for navigation telemetry"

    state.set_attitude(decode_attitude_state(encode_attitude_state(
        timestamp=Timestamp(seconds=10, nanoseconds=0),
        source="test-navigation",
        heading_rad=math.pi / 2,
        pitch_rad=math.pi / 12,
        roll_rad=-math.pi / 6,
    )))
    assert not state.snapshot().connected

    state.set_imu(decode_imu_state(encode_imu_state(
        timestamp=Timestamp(seconds=10, nanoseconds=0),
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


def test_error_disconnects_until_next_good_message():
    state = NavigationBusState()
    state.set_error("openroad.navigation.imu", RuntimeError("bad sample"))
    assert not state.snapshot().connected
    assert "bad sample" in state.snapshot().status
