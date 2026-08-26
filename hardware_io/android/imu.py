# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Android accelerometer and gyroscope hardware access."""

from __future__ import annotations

from dataclasses import dataclass

from .sensor_bridge_client import AndroidSensorBridgeClient
from controllers.navigation.navigation_types import Vector3


@dataclass(frozen=True, slots=True)
class ImuSample:
    acceleration_mps2: Vector3
    linear_acceleration_mps2: Vector3 | None
    angular_velocity_rad_s: Vector3
    timestamp_ns: int | None


class AndroidImu:
    """Read Android IMU measurements through the localhost bridge."""

    def __init__(self, client: AndroidSensorBridgeClient | None = None) -> None:
        self._client = client or AndroidSensorBridgeClient()

    @property
    def is_connected(self) -> bool:
        return self._client.is_available

    def connect(self) -> None:
        self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    def read(self) -> ImuSample:
        sample = self._client.read_imu()
        linear = sample.linear_acceleration_mps2 if sample.linear_acceleration_available else None
        timestamp = max(sample.accelerometer_timestamp_ns, sample.gyroscope_timestamp_ns) or None
        return ImuSample(
            acceleration_mps2=sample.acceleration_mps2,
            linear_acceleration_mps2=linear,
            angular_velocity_rad_s=sample.angular_velocity_rad_s,
            timestamp_ns=timestamp,
        )
