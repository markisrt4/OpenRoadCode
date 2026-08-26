# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish Android bridge hardware samples onto the OpenRoadCode message bus."""

from __future__ import annotations

from hardware_io.android import AndroidSensorBridgeClient
from messaging.publisher_if import PublisherIf

ANDROID_IMU_TOPIC = "android.imu"


class AndroidSensorService:
    """Forward the Android localhost IMU stream onto the OpenRoadCode message bus."""

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
        """Forward streamed IMU samples until interrupted."""
        for sample in self._client.stream_imu():
            self._publisher.publish(
                ANDROID_IMU_TOPIC,
                {
                    "acceleration_mps2": {
                        "x": sample.acceleration_mps2.x,
                        "y": sample.acceleration_mps2.y,
                        "z": sample.acceleration_mps2.z,
                    },
                    "angular_velocity_rad_s": {
                        "x": sample.angular_velocity_rad_s.x,
                        "y": sample.angular_velocity_rad_s.y,
                        "z": sample.angular_velocity_rad_s.z,
                    },
                    "accelerometer_timestamp_ns": sample.accelerometer_timestamp_ns,
                    "gyroscope_timestamp_ns": sample.gyroscope_timestamp_ns,
                },
            )
