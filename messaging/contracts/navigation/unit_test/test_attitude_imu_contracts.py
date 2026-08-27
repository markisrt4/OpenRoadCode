# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for navigation attitude and IMU contracts."""

import math

import pytest

from messaging.contracts.navigation import (
    decode_attitude_state,
    decode_imu_state,
    encode_attitude_state,
    encode_imu_state,
)

TIMESTAMP = {"seconds": 1_700_000_000, "nanoseconds": 123_000_000}


def test_attitude_round_trip_uses_radians() -> None:
    payload = encode_attitude_state(
        timestamp=TIMESTAMP,
        source="simulated-navigation",
        heading_rad=math.pi,
        pitch_rad=0.1,
        roll_rad=-0.2,
    )

    message = decode_attitude_state(payload)

    assert message.source == "simulated-navigation"
    assert message.data.heading_rad == pytest.approx(math.pi)
    assert message.data.pitch_rad == pytest.approx(0.1)
    assert message.data.roll_rad == pytest.approx(-0.2)


def test_attitude_rejects_invalid_heading_range() -> None:
    with pytest.raises(ValueError, match="heading_rad"):
        encode_attitude_state(
            timestamp=TIMESTAMP,
            source="imu",
            heading_rad=2.0 * math.pi,
        )


def test_imu_round_trip_preserves_si_vectors() -> None:
    payload = encode_imu_state(
        timestamp=TIMESTAMP,
        source="simulated-navigation",
        acceleration_m_s2={"x": 1.0, "y": 2.0, "z": 9.81},
        linear_acceleration_m_s2={"x": 0.1, "y": 0.2, "z": 0.3},
        angular_velocity_rad_s={"x": 0.01, "y": 0.02, "z": 0.03},
    )

    message = decode_imu_state(payload)

    assert message.data.acceleration_m_s2.z == pytest.approx(9.81)
    assert message.data.linear_acceleration_m_s2.x == pytest.approx(0.1)
    assert message.data.angular_velocity_rad_s.y == pytest.approx(0.02)


def test_imu_rejects_non_finite_axis() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        encode_imu_state(
            timestamp=TIMESTAMP,
            source="imu",
            acceleration_m_s2={"x": math.nan, "y": 0.0, "z": 9.81},
            linear_acceleration_m_s2={"x": 0.0, "y": 0.0, "z": 0.0},
            angular_velocity_rad_s={"x": 0.0, "y": 0.0, "z": 0.0},
        )
