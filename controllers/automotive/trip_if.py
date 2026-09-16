# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Domain contract for automotive trip tracking."""

from abc import ABC, abstractmethod
from datetime import datetime

from controllers.automotive.trip_state import TripState
from controllers.automotive.vehicle_state import VehicleState
from controllers.navigation.navigation_state import GroundMotionState, PositionState


class TripIf(ABC):
    """Accumulate vehicle and navigation observations into trip state.

    Implementations own trip lifecycle policy and derived calculations.
    Messaging, persistence, and presentation remain outside this contract.
    """

    @abstractmethod
    def observe_vehicle_state(self, state: VehicleState) -> None:
        """Consume one normalized vehicle telemetry snapshot.

        @param state SI-normalized vehicle telemetry snapshot.
        """
        ...

    @abstractmethod
    def observe_position_state(self, state: PositionState) -> None:
        """Consume one normalized geographic position snapshot.

        @param state Normalized geographic position snapshot.
        """
        ...

    @abstractmethod
    def observe_ground_motion_state(self, state: GroundMotionState) -> None:
        """Consume one normalized ground-motion snapshot.

        @param state Normalized ground-motion snapshot.
        """
        ...

    @abstractmethod
    def snapshot(self) -> TripState:
        """Return the current immutable trip snapshot.

        @return Current immutable trip state.
        """
        ...

    @abstractmethod
    def finish(self, ended_at: datetime | None = None) -> TripState:
        """Finish the current trip and return its final snapshot.

        @param ended_at Explicit trip end time, or None to use the implementation's current time.
        @return Final immutable trip state.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Discard current trip state and return to idle."""
        ...
