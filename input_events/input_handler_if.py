"""Consumer contract for normalized physical input events."""

from abc import ABC, abstractmethod

from input_events.input_event import InputEvent


class InputHandlerIf(ABC):
    """Consume generic physical input events without assigning ownership."""

    @abstractmethod
    def handle_input_event(self, event: InputEvent) -> None:
        """Handle one generic physical input event.

        @param event Normalized physical input event to handle.
        """
        ...
