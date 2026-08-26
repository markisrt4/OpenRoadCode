# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation motion source backed by Termux:API sensors."""

from __future__ import annotations

import json
import shutil
import subprocess

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.imu import Vector3


class TermuxNavigationSensor(NavigationSensorIf):
    """Read Android accelerometer and gyroscope samples through Termux:API."""

    def __init__(
        self,
        *,
        accelerometer_name: str = "Accelerometer",
        gyroscope_name: str = "Gyroscope",
    ) -> None:
        self._accelerometer_name = accelerometer_name
        self._gyroscope_name = gyroscope_name
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if shutil.which("termux-sensor") is None:
            raise RuntimeError("termux-sensor is not available; install Termux:API and the termux-api package")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_motion(self) -> MotionSample:
        if not self._connected:
            raise RuntimeError("Termux navigation sensor is not connected")

        acceleration = self._read_vector(self._accelerometer_name)
        angular_velocity = self._read_vector(self._gyroscope_name)
        return MotionSample(
            acceleration_mps2=acceleration,
            angular_velocity_rad_s=angular_velocity,
        )

    @staticmethod
    def _read_vector(sensor_name: str) -> Vector3:
        result = subprocess.run(
            ["termux-sensor", "-s", sensor_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict) or not payload:
            raise RuntimeError(f"No data returned for Termux sensor {sensor_name!r}")

        entry = next(iter(payload.values()))
        if not isinstance(entry, dict):
            raise RuntimeError(f"Unexpected Termux sensor payload for {sensor_name!r}")
        values = entry.get("values")
        if not isinstance(values, list) or len(values) < 3:
            raise RuntimeError(f"Termux sensor {sensor_name!r} did not return a 3-axis sample")

        return Vector3(float(values[0]), float(values[1]), float(values[2]))
