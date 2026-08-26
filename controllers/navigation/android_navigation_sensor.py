# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation sensor backed by the OpenRoadCode Android Bridge."""

from __future__ import annotations

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.android import AndroidSensorBridgeClient


class AndroidNavigationSensor(NavigationSensorIf):
    """Expose Android bridge IMU data through the navigation sensor contract."""

    def __init__(self, client: AndroidSensorBridgeClient | None = None) -> None:
        self._client = client or AndroidSensorBridgeClient()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client.is_available

    def connect(self) -> None:
        if not self._client.is_available:
            raise RuntimeError("OpenRoadCode Android sensor bridge is unavailable or not ready")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_motion(self) -> MotionSample:
        if not self._connected:
            raise RuntimeError("Android navigation sensor is not connected")
        sample = self._client.read_imu()
        return MotionSample(
            acceleration_mps2=sample.acceleration_mps2,
            angular_velocity_rad_s=sample.angular_velocity_rad_s,
        )
