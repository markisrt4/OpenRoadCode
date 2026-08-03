"""High-level automotive UI status contract."""

from abc import ABC, abstractmethod
from enum import Enum, auto

from ..ui_if import UiIf


class VehicleStatus(Enum):
    """Connection state displayed by an automotive UI."""

    UNKNOWN = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()


class AutomotiveUiIf(UiIf, ABC):
    """Display high-level vehicle connection status."""

    @abstractmethod
    def set_vehicle_status(self, status: VehicleStatus) -> None:
        """Set the displayed vehicle status.

        @param status Vehicle connection status to display.
        """
        ...
