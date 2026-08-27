# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic simulated motion input for the navigation solution."""

from __future__ import annotations

import math

from hardware_io.imu import Vector3

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf


class SimulatedNavigationSensor(NavigationSensorIf):
    """Provide repeatable IMU-like motion without physical sensor hardware."""

    def __init__(self, profile: str = "driving", step_radians: float = 0.08) -> None:
        self._profile = profile.strip().lower()
        self._step_radians = step_radians
        self._phase = 0.0
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_motion(self) -> MotionSample:
        if not self._connected:
            raise RuntimeError("simulated navigation sensor is not connected")

        if self._profile == "stationary":
            return MotionSample(
                acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
                angular_velocity_rad_s=Vector3(0.0, 0.0, 0.0),
            )
        if self._profile != "driving":
            raise ValueError(f"unsupported simulated IMU profile: {self._profile}")

        self._phase += self._step_radians
        linear_x = 1.2 * math.sin(self._phase * 1.3)
        linear_y = 0.8 * math.cos(self._phase)
        linear_z = 0.15 * math.sin(self._phase * 0.5)
        return MotionSample(
            acceleration_mps2=Vector3(
                linear_x,
                linear_y,
                9.80665 + linear_z,
            ),
            angular_velocity_rad_s=Vector3(0.01, 0.02, 0.04),
        )
