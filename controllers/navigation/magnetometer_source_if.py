# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Controller-facing magnetometer source contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class MagnetometerSample:
    """One normalized magnetic-field sample."""

    magnetic_field_ut: Vector3
    timestamp_ns: int | None = None


class MagnetometerSourceIf(ABC):
    """Provide normalized three-axis magnetic-field measurements."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the source is connected and ready.

        @return ``True`` when magnetic-field samples can be read.
        """

    @abstractmethod
    def connect(self) -> None:
        """Connect to the magnetometer source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the magnetometer source."""

    @abstractmethod
    def read_magnetometer(self) -> MagnetometerSample:
        """Read magnetic field strength in microteslas along each device axis.

        @return Normalized magnetic-field sample and optional source timestamp.
        """
