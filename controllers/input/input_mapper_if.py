from abc import ABC, abstractmethod

from controllers.input.input_types import InputEvent
from ui.ui_action import UiAction


class InputMapperIf(ABC):

    @abstractmethod
    def map_input(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        """Map an InputEvent into a UiAction."""
        ...
