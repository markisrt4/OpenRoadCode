"""Pushbutton event callback interface."""

from abc import ABC, abstractmethod


class PushButtonCallbackIf(ABC):
    """Receives physical pushbutton state-change events."""

    @abstractmethod
    def pressed(self) -> None:
        """Handle a transition to the pressed state."""

    @abstractmethod
    def released(self) -> None:
        """Handle a transition to the released state."""
