# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt Termux:API motion sensors to the navigation sensor contract."""

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.termux_api import TermuxSensorClient


class TermuxNavigationAdapter(NavigationSensorIf):
    """Provide normalized Android accelerometer and gyroscope samples."""

    def __init__(
        self,
        sensor: TermuxSensorClient,
        *,
        accelerometer_name: str = "Accelerometer",
        gyroscope_name: str = "Gyroscope",
    ) -> None:
        self._sensor = sensor
        self._accelerometer_name = accelerometer_name
        self._gyroscope_name = gyroscope_name
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if not self._sensor.is_available:
            raise RuntimeError("Termux:API sensor access is unavailable")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_motion(self) -> MotionSample:
        if not self._connected:
            raise RuntimeError("Termux navigation adapter is not connected")

        return MotionSample(
            acceleration_mps2=self._sensor.read_vector(self._accelerometer_name),
            angular_velocity_rad_s=self._sensor.read_vector(self._gyroscope_name),
        )
