"""Unavailable implementation for systems without a barometric sensor."""

from __future__ import annotations

from .barometric_controller_if import BarometricControllerIf
from .barometric_state import BarometricState


class UnconfiguredBarometricController(BarometricControllerIf):
    """Report that barometric support has not been configured."""

    STANDARD_SEA_LEVEL_PRESSURE_PA = 101_325.0

    def __init__(
        self,
        reason: str = "Barometric sensor is not configured",
    ) -> None:
        self._reason = reason

    @property
    def is_started(self) -> bool:
        return False

    @property
    def is_available(self) -> bool:
        return False

    @property
    def status_message(self) -> str | None:
        return self._reason

    @property
    def sea_level_pressure_pa(self) -> float:
        return self.STANDARD_SEA_LEVEL_PRESSURE_PA

    @property
    def latest_state(self) -> BarometricState | None:
        return None

    def start(self) -> None:
        self._raise_unavailable()

    def stop(self) -> None:
        pass

    def read_state(self) -> BarometricState:
        self._raise_unavailable()

    def set_sea_level_pressure_pa(self, pressure_pa: float) -> None:
        self._raise_unavailable()

    def calibrate_altitude(
        self,
        known_altitude_m: float,
        *,
        pressure_pa: float | None = None,
    ) -> float:
        self._raise_unavailable()

    def reset_relative_altitude(self) -> None:
        self._raise_unavailable()

    def _raise_unavailable(self) -> None:
        raise RuntimeError(self._reason)
