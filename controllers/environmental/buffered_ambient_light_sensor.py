# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Controller-facing ambient light sensor fed by an external sample stream."""

from __future__ import annotations

from hardware_io.environmental import AmbientLightSensorIf


class BufferedAmbientLightSensor(AmbientLightSensorIf):
    """Store the latest pushed illuminance for ``AmbientLightController``."""

    def __init__(self) -> None:
        self._started = False
        self._illuminance_lux: float | None = None

    @property
    def is_started(self) -> bool:
        return self._started

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def update_illuminance_lux(self, illuminance_lux: float) -> None:
        self._illuminance_lux = float(illuminance_lux)

    def get_illuminance_lux(self) -> float:
        if not self._started:
            raise RuntimeError("Buffered ambient light sensor is not started")
        if self._illuminance_lux is None:
            raise RuntimeError("No ambient light sample has been supplied")
        return self._illuminance_lux
