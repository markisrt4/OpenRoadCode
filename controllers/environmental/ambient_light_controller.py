# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Ambient light measurement controller."""

from __future__ import annotations

from datetime import datetime, timezone
import math

from hardware_io.environmental import AmbientLightSensorIf

from .ambient_light_controller_if import AmbientLightControllerIf
from .ambient_light_state import AmbientLightState


class AmbientLightController(AmbientLightControllerIf):
    """Provide validated ambient illuminance from a configured sensor."""

    def __init__(self, sensor: AmbientLightSensorIf) -> None:
        self._sensor = sensor
        self._latest_state: AmbientLightState | None = None

    @property
    def is_started(self) -> bool:
        return self._sensor.is_started

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def latest_state(self) -> AmbientLightState | None:
        return self._latest_state

    def start(self) -> None:
        self._sensor.start()

    def stop(self) -> None:
        self._sensor.stop()

    def read_state(self) -> AmbientLightState:
        if not self.is_started:
            raise RuntimeError("Ambient light controller is not started")

        illuminance_lux = float(self._sensor.get_illuminance_lux())
        if not math.isfinite(illuminance_lux) or illuminance_lux < 0.0:
            raise RuntimeError("Ambient light sensor returned invalid illuminance")

        state = AmbientLightState(
            timestamp=datetime.now(timezone.utc),
            illuminance_lux=illuminance_lux,
        )
        self._latest_state = state
        return state
