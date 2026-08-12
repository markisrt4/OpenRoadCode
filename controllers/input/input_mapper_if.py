# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from input_events import InputEvent
from ui.ui_action import UiAction


class InputMapperIf(ABC):

    @abstractmethod
    def map_input(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        """Map a physical input event into a semantic UI action.

        @param event Normalized physical input event to map.
        @return Mapped UI action, or None when the event has no mapping.
        """
        ...
