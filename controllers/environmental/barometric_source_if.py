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
        """Return whether the sensor is connected and ready.

        @retval True The sensor is connected and ready.
        @retval False The sensor is disconnected or unavailable.
        """

    @abstractmethod
    def connect(self) -> None:
        """Connect to the barometric source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the barometric source."""

    @abstractmethod
    def read_barometric(self) -> BarometricSample:
        """Read pressure in pascals and temperature in degrees Celsius.

        @return Normalized barometric sample in SI units.
        """

    def read_environment(self) -> BarometricSample:
        """Compatibility alias for the original generic source API.

        @return Normalized barometric sample in SI units.
        """
        return self.read_barometric()
