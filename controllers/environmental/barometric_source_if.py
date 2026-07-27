"""Controller-facing barometric source contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BarometricSample:
    """One normalized barometric sample in SI units."""

    pressure_pa: float
    temperature_c: float


class BarometricSourceIf(ABC):
    """Provide normalized measurements to a barometric controller."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the sensor is connected and ready."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the barometric source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the barometric source."""

    @abstractmethod
    def read_barometric(self) -> BarometricSample:
        """Read pressure in pascals and temperature in degrees Celsius."""

    def read_environment(self) -> BarometricSample:
        """Compatibility alias for the original generic source API."""
        return self.read_barometric()

