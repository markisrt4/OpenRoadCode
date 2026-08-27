# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Android accelerometer and gyroscope hardware access."""

from __future__ import annotations

from dataclasses import dataclass

from hardware_io.imu.imu_types import Vector3

from .sensor_bridge_client import AndroidSensorBridgeClient


@dataclass(frozen=True, slots=True)
class ImuSample:
    acceleration_mps2: Vector3
    linear_acceleration_mps2: Vector3 | None
    angular_velocity_rad_s: Vector3
    timestamp_ns: int | None


class AndroidImu:
    """Read Android IMU measurements through the localhost bridge.

    The HTTP bridge client itself is stateless, so connection state is owned by
    this hardware abstraction. ``connect()`` verifies that the bridge is ready;
    ``disconnect()`` simply marks this logical device disconnected.
    """

    def __init__(self, client: AndroidSensorBridgeClient | None = None) -> None:
        self._client = client or AndroidSensorBridgeClient()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client.is_available

    def connect(self) -> None:
        if not self._client.is_available:
            raise RuntimeError("Android IMU bridge is unavailable or not ready")
        self._client.read_imu()
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read(self) -> ImuSample:
        if not self._connected:
            raise RuntimeError("Android IMU is not connected")
        sample = self._client.read_imu()
        linear = _vector(sample.linear_acceleration_mps2) if sample.linear_acceleration_available else None
        timestamp = max(sample.accelerometer_timestamp_ns, sample.gyroscope_timestamp_ns) or None
        return ImuSample(
            acceleration_mps2=_vector(sample.acceleration_mps2),
            linear_acceleration_mps2=linear,
            angular_velocity_rad_s=_vector(sample.angular_velocity_rad_s),
            timestamp_ns=timestamp,
        )


def _vector(value: object) -> Vector3:
    return Vector3(x=float(getattr(value, "x")), y=float(getattr(value, "y")), z=float(getattr(value, "z")))
