# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Android IMU adaptation into the ORC vehicle frame."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.navigation.android_navigation_sensor import AndroidNavigationSensor
from hardware_io.android.imu import ImuSample
from hardware_io.imu import Vector3


@dataclass
class _FakeAndroidImu:
    sample: ImuSample
    connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self.connected

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def read(self) -> ImuSample:
        if not self.connected:
            raise RuntimeError("Android IMU is not connected")
        return self.sample


def test_android_motion_is_rotated_into_vehicle_frame() -> None:
    imu = _FakeAndroidImu(
        ImuSample(
            acceleration_mps2=Vector3(x=1.0, y=2.0, z=3.0),
            linear_acceleration_mps2=None,
            angular_velocity_rad_s=Vector3(x=4.0, y=5.0, z=6.0),
            timestamp_ns=123,
        )
    )
    sensor = AndroidNavigationSensor(imu=imu)  # type: ignore[arg-type]

    sensor.connect()
    sample = sensor.read_motion()

    assert sample.acceleration_mps2 == Vector3(x=2.0, y=-1.0, z=3.0)
    assert sample.angular_velocity_rad_s == Vector3(x=5.0, y=-4.0, z=6.0)


def test_android_navigation_sensor_delegates_lifecycle() -> None:
    imu = _FakeAndroidImu(
        ImuSample(
            acceleration_mps2=Vector3(x=0.0, y=0.0, z=9.81),
            linear_acceleration_mps2=None,
            angular_velocity_rad_s=Vector3(x=0.0, y=0.0, z=0.0),
            timestamp_ns=None,
        )
    )
    sensor = AndroidNavigationSensor(imu=imu)  # type: ignore[arg-type]

    assert not sensor.is_connected
    sensor.connect()
    assert sensor.is_connected
    sensor.disconnect()
    assert not sensor.is_connected
