"""Interface for barometric sensor hardware."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BarometricSensorIf(ABC):
    """Interface for reading barometric sensor measurements.

    Implementations provide raw or device-compensated measurements directly
    from barometric sensor hardware. Higher-level calculations such as
    altitude, pressure trends, and weather interpretation belong outside the
    hardware layer.
    """

    @abstractmethod
    def start(self) -> None:
        """Initialize the sensor and prepare it for use."""

    @abstractmethod
    def stop(self) -> None:
        """Release resources owned by the sensor."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the sensor has been initialized."""

    @abstractmethod
    def get_pressure_pa(self) -> float:
        """Return atmospheric pressure in pascals."""

    @abstractmethod
    def get_temperature_c(self) -> float:
        """Return the sensor temperature in degrees Celsius."""