# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt Termux:API motion streams to the navigation sensor contract."""

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.termux_api import TermuxSensorClient, TermuxSensorStream


class TermuxNavigationAdapter(NavigationSensorIf):
    """Provide normalized Android accelerometer and gyroscope samples."""

    def __init__(
        self,
        sensor: TermuxSensorClient,
        *,
        accelerometer_name: str = "Accelerometer",
        gyroscope_name: str = "Gyroscope",
        stream_delay_ms: int = 20,
    ) -> None:
        self._sensor = sensor
        self._accelerometer = TermuxSensorStream(
            accelerometer_name,
            delay_ms=stream_delay_ms,
        )
        self._gyroscope = TermuxSensorStream(
            gyroscope_name,
            delay_ms=stream_delay_ms,
        )
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if not self._sensor.is_available:
            raise RuntimeError("Termux:API sensor access is unavailable")

        self._accelerometer.start()
        self._gyroscope.start()
        try:
            if not self._accelerometer.wait_for_sample():
                raise RuntimeError("Timed out waiting for Termux accelerometer stream")
            if not self._gyroscope.wait_for_sample():
                raise RuntimeError("Timed out waiting for Termux gyroscope stream")
        except BaseException:
            self._accelerometer.stop()
            self._gyroscope.stop()
            raise
        self._connected = True

    def disconnect(self) -> None:
        self._accelerometer.stop()
        self._gyroscope.stop()
        self._connected = False

    def read_motion(self) -> MotionSample:
        if not self._connected:
            raise RuntimeError("Termux navigation adapter is not connected")

        acceleration, _ = self._accelerometer.latest()
        angular_velocity, _ = self._gyroscope.latest()
        return MotionSample(
            acceleration_mps2=acceleration,
            angular_velocity_rad_s=angular_velocity,
        )
