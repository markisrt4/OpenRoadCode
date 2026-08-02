"""Interface for panels that handle semantic UI actions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ui.ui_action import UiAction


class PanelActionHandlerIf(ABC):
    """Interface implemented by panels that consume UI actions."""

    @abstractmethod
    def handle_ui_action(self, action: UiAction) -> bool:
        """Handle an action.

        Returns:
            True when the panel handled the action.
            False when the parent UI should handle it.
        """
        ...
