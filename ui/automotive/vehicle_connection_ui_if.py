# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief UI contract for vehicle telemetry-source availability."""

from abc import ABC, abstractmethod
from enum import Enum, auto

class VehicleConnectionState(Enum):
    """! @brief Connection state of the vehicle telemetry source."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


class VehicleConnectionUiIf(ABC):
    """! @brief Display vehicle telemetry-source availability."""

    @abstractmethod
    def set_connection_state(
        self,
        state: VehicleConnectionState | None,
    ) -> None:
        """! @brief Set or clear the vehicle connection state.

        @param state Current connection state, or None when unavailable.
        """
        ...
