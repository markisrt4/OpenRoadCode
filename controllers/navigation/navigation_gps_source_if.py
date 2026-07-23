"""Navigation-facing GPS source interface."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from controllers.navigation.navigation_state import GpsState


GpsStateCallback = Callable[[GpsState], None]


class NavigationGpsSourceIf(ABC):
    """Publish normalized GPS state to the navigation controller."""

    @abstractmethod
    def start(self, callback: GpsStateCallback) -> None:
        """Start publishing GPS updates.

        @param callback Function invoked with each normalized GPS snapshot.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop publishing GPS updates."""
