"""! @brief UI contract for vehicle body and occupant state."""

from abc import ABC, abstractmethod
from enum import Enum, auto

from ..ui_if import UiIf


class VehicleOpening(Enum):
    """! @brief Door or panel that may be open or closed."""

    FRONT_LEFT_DOOR = auto()
    FRONT_RIGHT_DOOR = auto()
    REAR_LEFT_DOOR = auto()
    REAR_RIGHT_DOOR = auto()
    HOOD = auto()
    TRUNK = auto()


class SeatPosition(Enum):
    """! @brief Occupant seat monitored by the vehicle."""

    DRIVER = auto()
    FRONT_PASSENGER = auto()
    REAR_LEFT = auto()
    REAR_CENTER = auto()
    REAR_RIGHT = auto()


class ExteriorLight(Enum):
    """! @brief Exterior light state visible to the driver."""

    HEADLIGHTS = auto()
    HIGH_BEAMS = auto()
    LEFT_TURN_SIGNAL = auto()
    RIGHT_TURN_SIGNAL = auto()
    HAZARD_LIGHTS = auto()


class VehicleBodyUiIf(UiIf, ABC):
    """! @brief Display independently updated body and occupant state."""

    @abstractmethod
    def set_opening_state(
        self,
        opening: VehicleOpening,
        is_open: bool | None,
    ) -> None:
        """! @brief Set whether one door or panel is open.

        @param opening Door or panel whose state changed.
        @param is_open Open state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_seat_belt_state(
        self,
        seat: SeatPosition,
        fastened: bool | None,
    ) -> None:
        """! @brief Set whether one seat belt is fastened.

        @param seat Seat whose belt state changed.
        @param fastened Fastened state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_exterior_light_state(
        self,
        light: ExteriorLight,
        active: bool | None,
    ) -> None:
        """! @brief Set whether one exterior light function is active.

        @param light Exterior light function whose state changed.
        @param active Active state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_parking_brake(self, applied: bool | None) -> None:
        """! @brief Set the parking-brake state.

        @param applied Applied state, or None when unavailable.
        """
        ...
