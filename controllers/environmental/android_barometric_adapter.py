# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Barometric controller adapter backed by Android hardware I/O."""

from __future__ import annotations

from hardware_io.android.barometer import AndroidBarometer

from .barometric_source_if import BarometricSample, BarometricSourceIf


class AndroidBarometricAdapter(BarometricSourceIf):
    """Expose ``AndroidBarometer`` through ``BarometricSourceIf``."""

    def __init__(self, barometer: AndroidBarometer | None = None) -> None:
        self._barometer = barometer or AndroidBarometer()

    @property
    def is_connected(self) -> bool:
        return self._barometer.is_connected

    def connect(self) -> None:
        self._barometer.connect()
        self._barometer.read()

    def disconnect(self) -> None:
        self._barometer.disconnect()

    def read_barometric(self) -> BarometricSample:
        sample = self._barometer.read()
        return BarometricSample(pressure_pa=sample.pressure_pa, temperature_c=None)
