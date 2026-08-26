# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Barometric source backed by the localhost Android sensor bridge."""

from __future__ import annotations

from hardware_io.android import AndroidSensorBridgeClient

from .barometric_source_if import BarometricSample, BarometricSourceIf


class AndroidBarometricAdapter(BarometricSourceIf):
    """Expose the Android pressure sensor through ``BarometricSourceIf``."""

    def __init__(self, client: AndroidSensorBridgeClient) -> None:
        self._client = client
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client.is_available

    def connect(self) -> None:
        sample = self._client.read_imu()
        if not sample.pressure_available:
            raise RuntimeError("Android pressure sensor is unavailable")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_barometric(self) -> BarometricSample:
        if not self._connected:
            raise RuntimeError("Android barometric source is not connected")

        sample = self._client.read_imu()
        if not sample.pressure_available:
            raise RuntimeError("Android pressure sensor is unavailable")

        return BarometricSample(
            pressure_pa=sample.pressure_hpa * 100.0,
            temperature_c=None,
        )
