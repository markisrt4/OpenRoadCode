# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish Android bridge hardware samples onto the OpenRoadCode message bus."""

from __future__ import annotations

from datetime import datetime, timezone

from hardware_io.android import AndroidImu, AndroidMagnetometer, AndroidSensorBridgeClient
from messaging.contracts.common.timestamp import encode_timestamp
from messaging.contracts.navigation.imu_state_codec import encode_imu_state
from messaging.contracts.navigation.magnetic_field_state_codec import encode_magnetic_field_state
from messaging.contracts.navigation.topics import IMU_STATE_TOPIC, MAGNETIC_FIELD_STATE_TOPIC
from messaging.publisher_if import PublisherIf

ANDROID_SENSOR_SOURCE = "android"
_ZERO_VECTOR = {"x": 0.0, "y": 0.0, "z": 0.0}


class AndroidSensorService:
    """Forward Android navigation sensors onto the OpenRoadCode message bus."""

    def __init__(self, client: AndroidSensorBridgeClient, publisher: PublisherIf, *, poll_hz: float | None = None) -> None:
        if poll_hz is not None and poll_hz <= 0.0:
            raise ValueError("poll_hz must be greater than zero")
        self._client = client
        self._publisher = publisher
        self._magnetometer = AndroidMagnetometer(client)

    def run(self) -> None:
        """Forward streamed IMU samples and available magnetic-field samples."""
        for sample in self._client.stream_imu():
            timestamp = encode_timestamp(datetime.now(timezone.utc))
            linear = _vector_dict(sample.linear_acceleration_mps2) if sample.linear_acceleration_available else _ZERO_VECTOR
            self._publisher.publish(IMU_STATE_TOPIC, encode_imu_state(
                timestamp=timestamp,
                source=ANDROID_SENSOR_SOURCE,
                acceleration_m_s2=_vector_dict(sample.acceleration_mps2),
                linear_acceleration_m_s2=linear,
                angular_velocity_rad_s=_vector_dict(sample.angular_velocity_rad_s),
            ))
            if sample.magnetometer_available:
                self._publisher.publish(MAGNETIC_FIELD_STATE_TOPIC, encode_magnetic_field_state(
                    timestamp=timestamp,
                    source=ANDROID_SENSOR_SOURCE,
                    magnetic_field_ut=_vector_dict(sample.magnetic_field_ut),
                ))


def _vector_dict(vector: object) -> dict[str, float]:
    return {axis: float(getattr(vector, axis)) for axis in ("x", "y", "z")}
