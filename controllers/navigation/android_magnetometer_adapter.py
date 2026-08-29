# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Magnetometer source backed by Android hardware I/O."""

from __future__ import annotations

from hardware_io.android import AndroidMagnetometer
from hardware_io.imu import Vector3

from .magnetometer_source_if import MagnetometerSample, MagnetometerSourceIf


class AndroidMagnetometerAdapter(MagnetometerSourceIf):
    """Adapt Android device-frame magnetic field to the ORC vehicle frame.

    The default phone mount is portrait and screen-up with the top of the phone
    pointing toward the vehicle front. Android +X points toward the phone's
    right edge, +Y toward its top, and +Z out of the screen. The ORC vehicle
    frame is right-handed with +X forward, +Y left, and +Z up.
    """

    def __init__(self, magnetometer: AndroidMagnetometer) -> None:
        self._magnetometer = magnetometer

    @property
    def is_connected(self) -> bool:
        return self._magnetometer.is_connected

    def connect(self) -> None:
        self._magnetometer.connect()

    def disconnect(self) -> None:
        self._magnetometer.disconnect()

    def read_magnetometer(self) -> MagnetometerSample:
        sample = self._magnetometer.read_magnetometer()
        field = sample.magnetic_field_ut
        return MagnetometerSample(
            magnetic_field_ut=Vector3(
                x=field.y,
                y=-field.x,
                z=field.z,
            ),
            timestamp_ns=sample.timestamp_ns,
        )
