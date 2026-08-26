# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish Android bridge hardware samples onto the OpenRoadCode message bus."""

from __future__ import annotations

from datetime import datetime, timezone

from hardware_io.android import AndroidSensorBridgeClient
from messaging.contracts.common.timestamp import encode_timestamp
from messaging.contracts.navigation.imu_state_codec import encode_imu_state
from messaging.contracts.navigation.topics import IMU_STATE_TOPIC
from messaging.publisher_if import PublisherIf

ANDROID_IMU_SOURCE = "android"
_ZERO_VECTOR = {"x": 0.0, "y": 0.0, "z": 0.0}


class AndroidSensorService:
    """Forward the Android localhost IMU stream onto the navigation message bus."""

    def __init__(
        self,
        client: AndroidSensorBridgeClient,
        publisher: PublisherIf,
        *,
        poll_hz: float | None = None,
    ) -> None:
        # poll_hz is retained temporarily for callers from the snapshot implementation.
        # The persistent stream now determines the publication rate.
        if poll_hz is not None and poll_hz <= 0.0:
            raise ValueError("poll_hz must be greater than zero")
        self._client = client
        self._publisher = publisher

    def run(self) -> None:
        """Forward streamed Android samples using the standard navigation IMU contract."""
        for sample in self._client.stream_imu():
            acceleration = {
                "x": sample.acceleration_mps2.x,
                "y": sample.acceleration_mps2.y,
                "z": sample.acceleration_mps2.z,
            }
            angular_velocity = {
                "x": sample.angular_velocity_rad_s.x,
                "y": sample.angular_velocity_rad_s.y,
                "z": sample.angular_velocity_rad_s.z,
            }
            payload = encode_imu_state(
                timestamp=encode_timestamp(datetime.now(timezone.utc)),
                source=ANDROID_IMU_SOURCE,
                acceleration_m_s2=acceleration,
                # Android currently exposes acceleration including gravity through
                # this bridge. Do not pretend that we have independently measured
                # linear acceleration; that can be added when the bridge exposes it.
                linear_acceleration_m_s2=_ZERO_VECTOR,
                angular_velocity_rad_s=angular_velocity,
            )
            self._publisher.publish(IMU_STATE_TOPIC, payload)
