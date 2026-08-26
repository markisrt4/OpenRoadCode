# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Magnetometer source backed by the localhost Android sensor bridge."""

from __future__ import annotations

from hardware_io.android import AndroidSensorBridgeClient

from .magnetometer_source_if import MagnetometerSample, MagnetometerSourceIf


class AndroidMagnetometerAdapter(MagnetometerSourceIf):
    """Expose the Android magnetometer through ``MagnetometerSourceIf``."""

    def __init__(self, client: AndroidSensorBridgeClient) -> None:
        self._client = client
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client.is_available

    def connect(self) -> None:
        sample = self._client.read_imu()
        if not sample.magnetometer_available:
            raise RuntimeError("Android magnetometer is unavailable")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_magnetometer(self) -> MagnetometerSample:
        if not self._connected:
            raise RuntimeError("Android magnetometer source is not connected")

        sample = self._client.read_imu()
        if not sample.magnetometer_available:
            raise RuntimeError("Android magnetometer is unavailable")

        return MagnetometerSample(
            magnetic_field_ut=sample.magnetic_field_ut,
            timestamp_ns=sample.magnetometer_timestamp_ns,
        )
