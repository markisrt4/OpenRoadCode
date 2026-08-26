# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation sensor backed by Android IMU hardware I/O."""

from __future__ import annotations

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.android import AndroidImu


class AndroidNavigationSensor(NavigationSensorIf):
    """Expose ``AndroidImu`` through the navigation sensor contract."""

    def __init__(self, imu: AndroidImu | None = None) -> None:
        self._imu = imu or AndroidImu()

    @property
    def is_connected(self) -> bool:
        return self._imu.is_connected

    def connect(self) -> None:
        self._imu.connect()

    def disconnect(self) -> None:
        self._imu.disconnect()

    def read_motion(self) -> MotionSample:
        sample = self._imu.read()
        return MotionSample(
            acceleration_mps2=sample.acceleration_mps2,
            angular_velocity_rad_s=sample.angular_velocity_rad_s,
        )
