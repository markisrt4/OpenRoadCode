# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-neutral turn-by-turn route presentation contract."""

from abc import ABC, abstractmethod


class RouteGuidanceUiIf(ABC):
    """Display active turn-by-turn route guidance."""

    @abstractmethod
    def set_instruction(self, instruction: str | None) -> None:
        """Set the current maneuver instruction."""
        ...

    @abstractmethod
    def set_distance_to_maneuver(self, distance_m: float | None) -> None:
        """Set distance remaining until the current maneuver."""
        ...

    @abstractmethod
    def set_distance_remaining(self, distance_m: float | None) -> None:
        """Set total route distance remaining."""
        ...

    @abstractmethod
    def set_off_route(self, off_route: bool) -> None:
        """Set whether the vehicle is currently off route."""
        ...

    @abstractmethod
    def set_route_complete(self, complete: bool) -> None:
        """Set whether the destination has been reached."""
        ...
