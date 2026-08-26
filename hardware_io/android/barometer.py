# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Android barometer hardware access."""

from __future__ import annotations

from dataclasses import dataclass

from .sensor_bridge_client import AndroidSensorBridgeClient


@dataclass(frozen=True, slots=True)
class PressureSample:
    pressure_pa: float
    timestamp_ns: int | None


class AndroidBarometer:
    """Read Android pressure measurements through the localhost bridge."""

    def __init__(self, client: AndroidSensorBridgeClient | None = None) -> None:
        self._client = client or AndroidSensorBridgeClient()

    @property
    def is_connected(self) -> bool:
        return self._client.is_available

    def connect(self) -> None:
        self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    def read(self) -> PressureSample:
        sample = self._client.read_imu()
        if not sample.pressure_available:
            raise RuntimeError("Android pressure sensor is unavailable")
        return PressureSample(
            pressure_pa=sample.pressure_hpa * 100.0,
            timestamp_ns=sample.pressure_timestamp_ns or None,
        )
