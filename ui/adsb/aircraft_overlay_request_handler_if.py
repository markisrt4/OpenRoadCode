# SPDX-License-Identifier: MIT
"""Semantic aircraft map interactions."""

from abc import ABC, abstractmethod


class AircraftOverlayRequestHandlerIf(ABC):
    @abstractmethod
    def request_aircraft_visible(self, visible: bool) -> None:
        """Show or hide aircraft without changing SDR receiver ownership.
        @param visible Whether aircraft should be displayed.
        """
        ...

    @abstractmethod
    def request_aircraft_selection(self, icao: str | None) -> None:
        """Select an aircraft or dismiss details.
        @param icao Aircraft identifier, or None to dismiss details.
        """
        ...

    @abstractmethod
    def request_aircraft_follow(self, icao: str | None) -> None:
        """Follow an aircraft or release camera following.
        @param icao Aircraft identifier, or None to release following.
        """
        ...

    @abstractmethod
    def request_aircraft_replay(self) -> None:
        """Replay current state after renderer restart."""
        ...
