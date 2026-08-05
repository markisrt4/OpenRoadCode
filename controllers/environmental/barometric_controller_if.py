"""Public interface for environmental controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .barometric_state import BarometricState


class BarometricControllerIf(ABC):
    """Provide processed pressure, temperature, and altitude state."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the controller is ready to read state.

        @retval True The controller has been started.
        @retval False The controller has not been started.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether barometric support is configured and available.

        @retval True Barometric support is available.
        @retval False Barometric support is unavailable.
        """

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies.

        @return Human-readable status, or ``None`` when no message applies.
        """

    @property
    @abstractmethod
    def sea_level_pressure_pa(self) -> float:
        """Return the sea-level pressure reference in pascals.

        @return Active sea-level pressure reference in pascals.
        """

    @property
    @abstractmethod
    def latest_state(self) -> BarometricState | None:
        """Return the latest state, or ``None`` before the first read.

        @return Latest processed state, or ``None`` before the first read.
        """

    @abstractmethod
    def start(self) -> None:
        """Start the controller and its environmental source."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the controller and its environmental source."""

    @abstractmethod
    def read_state(self) -> BarometricState:
        """Read and return the current processed environmental state.

        @return Current pressure, temperature, and altitude state.
        """

    @abstractmethod
    def set_sea_level_pressure_pa(self, pressure_pa: float) -> None:
        """Set the pressure reference used for absolute altitude.

        @param pressure_pa Sea-level pressure reference in pascals.
        """

    @abstractmethod
    def calibrate_altitude(
        self,
        known_altitude_m: float,
        *,
        pressure_pa: float | None = None,
    ) -> float:
        """Calibrate sea-level pressure at a known altitude.

        @param known_altitude_m Known altitude in meters above sea level.
        @param pressure_pa Measured pressure in pascals, or ``None`` to read
            the current pressure from the configured source.
        @return Calibrated sea-level pressure reference in pascals.
        """

    @abstractmethod
    def reset_relative_altitude(self) -> None:
        """Set the current altitude as the relative-altitude zero point."""
