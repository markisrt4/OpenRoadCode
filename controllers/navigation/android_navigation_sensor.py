# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation sensor backed by Android IMU hardware I/O."""

from __future__ import annotations

from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from hardware_io.android import AndroidImu
from hardware_io.imu import Vector3


class AndroidNavigationSensor(NavigationSensorIf):
    """Expose ``AndroidImu`` through the navigation sensor contract.

    Android sensor coordinates are device-relative: +X points to the right edge
    of the screen, +Y points toward the top of the screen, and +Z points out of
    the screen. OpenRoadCode navigation uses a vehicle frame with +X forward,
    +Y left, and +Z up.

    The default phone mounting convention is portrait, screen facing up, with
    the top of the phone pointing toward the front of the vehicle. Under that
    convention the transform is::

        vehicle_x =  android_y
        vehicle_y = -android_x
        vehicle_z =  android_z

    The same rotation is applied to acceleration and angular velocity so the
    navigation estimator sees one consistent vehicle coordinate frame.
    """

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
            acceleration_mps2=_android_to_vehicle(sample.acceleration_mps2),
            angular_velocity_rad_s=_android_to_vehicle(
                sample.angular_velocity_rad_s
            ),
        )


def _android_to_vehicle(vector: Vector3) -> Vector3:
    """Rotate a portrait, screen-up Android vector into the ORC vehicle frame."""
    return Vector3(
        x=vector.y,
        y=-vector.x,
        z=vector.z,
    )
