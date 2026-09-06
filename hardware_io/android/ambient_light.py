# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Android ambient light sensor hardware access."""

from __future__ import annotations

from hardware_io.environmental import AmbientLightSensorIf

from .sensor_bridge_client import AndroidSensorBridgeClient


class AndroidAmbientLight(AmbientLightSensorIf):
    """Read Android illuminance measurements through the localhost bridge."""

    def __init__(self, client: AndroidSensorBridgeClient | None = None) -> None:
        self._client = client or AndroidSensorBridgeClient()
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started and self._client.is_available

    def start(self) -> None:
        sample = self._client.read_imu()
        if not sample.ambient_light_available:
            raise RuntimeError("Android ambient light sensor is unavailable")
        self._started = True

    def stop(self) -> None:
        self._started = False

    def get_illuminance_lux(self) -> float:
        if not self._started:
            raise RuntimeError("Android ambient light sensor is not started")
        sample = self._client.read_imu()
        if not sample.ambient_light_available:
            raise RuntimeError("Android ambient light sensor is unavailable")
        return sample.ambient_light_lux
