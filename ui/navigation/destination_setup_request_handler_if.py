# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent requests for configuring saved destinations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ui.navigation.map_ui_if import GeoPoint


@dataclass(frozen=True, slots=True)
class SavedDestination:
    """Confirmed address and position; angles are in radians."""

    key: str
    label: str
    address: str
    position: GeoPoint


class DestinationSetupRequestHandlerIf(ABC):
    """Resolve candidates and persist only explicitly confirmed destinations."""

    @abstractmethod
    def current(self, key: str) -> SavedDestination | None:
        """Read a configured destination.

        @param key Home or work.
        @return Existing destination, or None.
        """
        ...

    @abstractmethod
    def search(self, key: str, address: str) -> tuple[SavedDestination, ...]:
        """Resolve an address using local data without changing configuration.

        @param key Home or work.
        @param address Address entered by the user.
        @return Immutable candidates, or an empty tuple.
        """
        ...

    @abstractmethod
    def save(self, destination: SavedDestination) -> None:
        """Persist a destination after user confirmation.

        @param destination Confirmed address and normalized position.
        """
        ...
