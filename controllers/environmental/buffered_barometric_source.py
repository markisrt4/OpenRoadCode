# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Controller-facing barometric source fed by an external sample stream."""

from __future__ import annotations

from .barometric_source_if import BarometricSample, BarometricSourceIf


class BufferedBarometricSource(BarometricSourceIf):
    """Store the latest pushed sample for use by ``BarometricController``."""

    def __init__(self) -> None:
        self._connected = False
        self._sample: BarometricSample | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def update_sample(self, sample: BarometricSample) -> None:
        self._sample = sample

    def read_barometric(self) -> BarometricSample:
        if not self._connected:
            raise RuntimeError("Buffered barometric source is not connected")
        if self._sample is None:
            raise RuntimeError("No barometric sample has been supplied")
        return self._sample
