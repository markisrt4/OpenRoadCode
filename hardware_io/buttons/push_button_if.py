"""Pushbutton hardware interface."""

from abc import ABC, abstractmethod

from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.buttons.push_button_state import PushButtonState


class PushButtonIf(ABC):
    """Interface for a physical pushbutton."""

    @abstractmethod
    def start(self) -> None:
        """Begin monitoring the pushbutton."""

    @abstractmethod
    def stop(self) -> None:
        """Stop monitoring the pushbutton."""

    @abstractmethod
    def get_state(self) -> PushButtonState:
        """Return the current pushbutton state.

        @return Current pressed or released state.
        """

    @abstractmethod
    def set_callback(
        self,
        callback: PushButtonCallbackIf | None,
    ) -> None:
        """Set or clear the callback object.

        @param callback Event receiver, or ``None`` to disable notifications.
        """
