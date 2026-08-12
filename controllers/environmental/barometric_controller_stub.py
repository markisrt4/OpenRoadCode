# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic in-memory barometric controller."""

from __future__ import annotations

import math
from dataclasses import replace

from .barometric_controller_if import BarometricControllerIf
from .barometric_state import BarometricState


class BarometricControllerStub(BarometricControllerIf):
    """Provide configurable barometric state for demos and UI development."""

    STANDARD_SEA_LEVEL_PRESSURE_PA = 101_325.0

    def __init__(
        self,
        state: BarometricState | None = None,
        *,
        sea_level_pressure_pa: float = STANDARD_SEA_LEVEL_PRESSURE_PA,
    ) -> None:
        if sea_level_pressure_pa <= 0.0:
            raise ValueError(
                "sea_level_pressure_pa must be greater than zero"
            )

        self._state = state or BarometricState.create(
            pressure_pa=101_325.0,
            temperature_c=20.0,
            altitude_m=0.0,
            relative_altitude_m=0.0,
            vertical_speed_mps=0.0,
        )
        self._sea_level_pressure_pa = sea_level_pressure_pa
        self._started = False
        self._latest_state: BarometricState | None = None

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def sea_level_pressure_pa(self) -> float:
        return self._sea_level_pressure_pa

    @property
    def latest_state(self) -> BarometricState | None:
        return self._latest_state

    def start(self) -> None:
        self._started = True
        self._latest_state = None

    def stop(self) -> None:
        self._started = False

    def read_state(self) -> BarometricState:
        if not self._started:
            raise RuntimeError("Barometric controller has not been started")
        self._latest_state = self._state
        return self._state

    def set_state(self, state: BarometricState) -> None:
        """Replace the deterministic state returned by future reads."""
        self._state = state
        self._latest_state = None

    def set_sea_level_pressure_pa(self, pressure_pa: float) -> None:
        if pressure_pa <= 0.0:
            raise ValueError("pressure_pa must be greater than zero")
        self._sea_level_pressure_pa = pressure_pa
        self._latest_state = None

    def calibrate_altitude(
        self,
        known_altitude_m: float,
        *,
        pressure_pa: float | None = None,
    ) -> float:
        if not self._started:
            raise RuntimeError("Barometric controller has not been started")

        current_pressure_pa = (
            self._state.pressure_pa
            if pressure_pa is None
            else pressure_pa
        )
        if current_pressure_pa <= 0.0:
            raise ValueError("pressure_pa must be greater than zero")

        self._sea_level_pressure_pa = current_pressure_pa / math.pow(
            1.0 - (known_altitude_m / 44_330.0),
            5.255,
        )
        self._latest_state = None
        return self._sea_level_pressure_pa

    def reset_relative_altitude(self) -> None:
        if not self._started:
            raise RuntimeError("Barometric controller has not been started")
        self._state = replace(self._state, relative_altitude_m=0.0)
        self._latest_state = None
