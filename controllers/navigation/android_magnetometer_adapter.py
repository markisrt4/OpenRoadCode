# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Magnetometer source backed by Android hardware I/O."""

from __future__ import annotations

from hardware_io.android import AndroidMagnetometer

from .magnetometer_source_if import MagnetometerSample, MagnetometerSourceIf


class AndroidMagnetometerAdapter(MagnetometerSourceIf):
    """Adapt the Android hardware magnetometer to the navigation contract."""

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
        return MagnetometerSample(
            magnetic_field_ut=sample.magnetic_field_ut,
            timestamp_ns=sample.timestamp_ns,
        )
