# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief UI contract for independently updated tire information."""

from abc import ABC, abstractmethod
from enum import Enum, auto

class TirePosition(Enum):
    """! @brief Position of a tire on a four-wheel vehicle."""

    FRONT_LEFT = auto()
    FRONT_RIGHT = auto()
    REAR_LEFT = auto()
    REAR_RIGHT = auto()


class VehicleTireUiIf(ABC):
    """! @brief Display tire measurements in SI units."""

    @abstractmethod
    def set_tire_pressure(
        self,
        position: TirePosition,
        pressure_pa: float | None,
    ) -> None:
        """! @brief Set one tire's pressure.

        @param position Tire whose pressure changed.
        @param pressure_pa Pressure in pascals, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_tire_temperature(
        self,
        position: TirePosition,
        temperature_k: float | None,
    ) -> None:
        """! @brief Set one tire's temperature.

        @param position Tire whose temperature changed.
        @param temperature_k Temperature in kelvin, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_tire_pressure_warning(
        self,
        position: TirePosition,
        active: bool | None,
    ) -> None:
        """! @brief Set one tire's pressure-warning state.

        @param position Tire whose warning state changed.
        @param active Warning state, or None when unavailable.
        """
        ...
