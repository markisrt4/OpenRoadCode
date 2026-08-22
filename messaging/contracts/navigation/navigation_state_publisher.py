# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish attitude and IMU contracts from one NavigationState sample."""

from __future__ import annotations

import math

from controllers.navigation.navigation_state import NavigationState
from messaging.contracts.common import encode_timestamp
from messaging.publisher_if import PublisherIf

from .attitude_state_codec import encode_attitude_state
from .imu_state_codec import encode_imu_state
from .topics import ATTITUDE_STATE_TOPIC, IMU_STATE_TOPIC


class NavigationStatePublisher:
    """Fan one normalized navigation sample out to public telemetry topics."""

    def __init__(
        self,
        publisher: PublisherIf,
        *,
        source: str = "navigation-controller",
    ) -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, state: NavigationState) -> None:
        """Publish attitude and IMU messages with one shared sample timestamp."""
        timestamp = encode_timestamp(state.timestamp)

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
