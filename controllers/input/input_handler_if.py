from abc import ABC, abstractmethod

from controllers.input.input_types import InputEvent


class InputHandlerIf(ABC):

    @abstractmethod
    def handle_input_event(self, event: InputEvent) -> None:
        """Handle one generic physical input event."""
        ...
