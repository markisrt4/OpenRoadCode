# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent Aircraft menu state and semantic requests."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AircraftMenuUiState:
    adsb_enabled: bool = False
    aircraft_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "adsb_enabled", bool(self.adsb_enabled))
        object.__setattr__(self, "aircraft_count", max(0, int(self.aircraft_count)))


class AircraftMenuRequestHandlerIf(ABC):
    @abstractmethod
    def request_adsb_enabled(self, enabled: bool) -> None:
        """Request ADS-B receiver state without blocking the frontend thread."""

    @abstractmethod
    def request_open_tracker(self) -> None:
        """Open the 1090 aircraft tracker."""

    @abstractmethod
    def request_open_airband(self) -> None:
        """Open AM aviation radio."""
