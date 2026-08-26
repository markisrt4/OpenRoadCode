# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish Android bridge hardware samples onto the OpenRoadCode message bus."""

from __future__ import annotations

import time

from hardware_io.android import AndroidSensorBridgeClient
from messaging.publisher_if import PublisherIf

ANDROID_IMU_TOPIC = "android.imu"


class AndroidSensorService:
    """Poll the Android localhost bridge and publish normalized IMU samples."""

    def __init__(
        self,
        client: AndroidSensorBridgeClient,
        publisher: PublisherIf,
        *,
        poll_hz: float = 20.0,
    ) -> None:
        if poll_hz <= 0.0:
            raise ValueError("poll_hz must be greater than zero")
        self._client = client
        self._publisher = publisher
        self._period_seconds = 1.0 / poll_hz

    def run(self) -> None:
        """Publish IMU snapshots until interrupted."""
        while True:
            started = time.monotonic()
            sample = self._client.read_imu()
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
            remaining = self._period_seconds - (time.monotonic() - started)
            if remaining > 0.0:
                time.sleep(remaining)
