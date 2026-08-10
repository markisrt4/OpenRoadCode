"""Source contract for normalized geographic position updates."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from controllers.navigation.navigation_state import PositionState


PositionStateCallback = Callable[[PositionState], None]


class PositionSourceIf(ABC):
    """Publish positions independently of the underlying provider."""

    @abstractmethod
    def start(self, callback: PositionStateCallback) -> None:
        """Start publishing normalized position snapshots.

        @param callback Consumer invoked for each available position snapshot.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop publishing position snapshots."""
        ...
