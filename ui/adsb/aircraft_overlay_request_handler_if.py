# SPDX-License-Identifier: MIT
"""Semantic aircraft map interactions."""
from abc import ABC, abstractmethod


class AircraftOverlayRequestHandlerIf(ABC):
    @abstractmethod
    def request_aircraft_visible(self, visible: bool) -> None:
        """Show or hide aircraft without changing SDR receiver ownership."""
        ...

    @abstractmethod
    def request_aircraft_selection(self, icao: str | None) -> None:
        """Select an aircraft or dismiss details."""
        ...

    @abstractmethod
    def request_aircraft_follow(self, icao: str | None) -> None:
        """Follow an aircraft or release camera following."""
        ...

    @abstractmethod
    def request_aircraft_replay(self) -> None:
        """Replay current state after renderer restart."""
        ...
