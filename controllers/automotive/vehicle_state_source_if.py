# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source contract for complete vehicle telemetry snapshots."""

from abc import ABC, abstractmethod

from controllers.automotive.vehicle_state import VehicleState


class VehicleStateSourceIf(ABC):
    """Connect and publish complete vehicle-state snapshots."""

    @abstractmethod
    def connect(self) -> None:
        """Connect or activate the vehicle telemetry source."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect or deactivate the vehicle telemetry source."""
        ...

    @abstractmethod
    def read_state(self) -> VehicleState:
        """Return the latest vehicle telemetry snapshot.

        @return Current complete vehicle state.
        """
        ...
