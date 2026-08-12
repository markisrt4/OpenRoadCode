# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from ui.ui_action import UiAction


class UiEventHandlerIf(ABC):
    """! @brief Receive device-independent actions at the root UI boundary."""

    @abstractmethod
    def handle_ui_action(self, action: UiAction) -> None:
        """! @brief Route one normalized UI action.

        @param action Device-independent UI action to route.
        """
        ...
