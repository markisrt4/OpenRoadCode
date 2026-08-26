# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-facing Android magnetometer device."""

from __future__ import annotations

from dataclasses import dataclass

from hardware_io.android.sensor_bridge_client import AndroidSensorBridgeClient
from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class MagnetometerSample:
    """One normalized magnetic-field sample from hardware."""

    magnetic_field_ut: Vector3
    timestamp_ns: int | None = None


class AndroidMagnetometer:
    """Read the phone magnetometer through the localhost Android bridge."""

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
            raise RuntimeError("Android magnetometer is not connected")

        sample = self._client.read_imu()
        if not sample.magnetometer_available:
            raise RuntimeError("Android magnetometer is unavailable")

        return MagnetometerSample(
            magnetic_field_ut=sample.magnetic_field_ut,
            timestamp_ns=sample.magnetometer_timestamp_ns,
        )
