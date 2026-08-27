# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish public navigation contracts from one NavigationState sample."""

from __future__ import annotations

import math

from controllers.navigation.navigation_state import NavigationState
from messaging.contracts.common import encode_timestamp
from messaging.publisher_if import PublisherIf

from .attitude_state_codec import encode_attitude_state
from .imu_state_codec import encode_imu_state
from .motion_state_codec import encode_motion_state
from .position_state_codec import encode_position_state
from .topics import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
)


class NavigationStatePublisher:
    """Fan one normalized navigation sample out to public telemetry topics.

    Attitude, IMU, and motion messages share the NavigationState timestamp.
    Position retains the position source timestamp because position fixes may
    update at a different cadence from the inertial sample.
    """

    def __init__(
        self,
        publisher: PublisherIf,
        *,
        source: str = "navigation-controller",
    ) -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, state: NavigationState) -> None:
        """Publish position, motion, attitude, and IMU telemetry.

        @param state One normalized navigation sample to fan out.
        """
        timestamp = encode_timestamp(state.timestamp)
        position = state.position
        ground_motion = state.ground_motion

        if position is not None:
            self._publisher.publish(
                POSITION_STATE_TOPIC,
                encode_position_state(position),
            )

        self._publisher.publish(
            MOTION_STATE_TOPIC,
            encode_motion_state(
                timestamp=timestamp,
                source=self._source,
                heading_rad=math.radians(state.heading_deg),
                ground_speed_m_s=(
                    None if ground_motion is None else ground_motion.speed_mps
                ),
                course_rad=(
                    None
                    if ground_motion is None or ground_motion.course_deg is None
                    else math.radians(ground_motion.course_deg)
                ),
                vertical_speed_m_s=None,
                turn_rate_rad_s=state.angular_velocity_rad_s.z,
                is_cached=False,
            ),
        )
        self._publisher.publish(
            ATTITUDE_STATE_TOPIC,
            encode_attitude_state(
                timestamp=timestamp,
                source=self._source,
                heading_rad=math.radians(state.heading_deg),
                pitch_rad=math.radians(state.pitch_deg),
                roll_rad=math.radians(state.roll_deg),
            ),
        )
        self._publisher.publish(
            IMU_STATE_TOPIC,
            encode_imu_state(
                timestamp=timestamp,
                source=self._source,
                acceleration_m_s2=_vector(state.acceleration_mps2),
                linear_acceleration_m_s2=_vector(state.linear_acceleration_mps2),
                angular_velocity_rad_s=_vector(state.angular_velocity_rad_s),
            ),
        )


def _vector(vector) -> dict[str, float]:
    return {
        "x": float(vector.x),
        "y": float(vector.y),
        "z": float(vector.z),
    }
