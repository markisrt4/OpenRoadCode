"""Toolkit-independent contract for navigation between UI screens."""

from abc import ABC, abstractmethod

from ui.screen_ui_if import ScreenId


class ScreenNavigatorIf(ABC):
    """Navigate between registered screens and expose navigation state."""

    @property
    @abstractmethod
    def active_screen_id(self) -> ScreenId | None:
        """Return the active screen identifier, if a screen is active.

        @return Active screen identifier, or None before navigation begins.
        """
        ...

    @abstractmethod
    def show_screen(self, screen_id: ScreenId) -> None:
        """Navigate to a screen and add the previous screen to history.

        @param screen_id Identifier of the registered destination screen.
        """
        ...

    @abstractmethod
    def go_back(self) -> bool:
        """Return to the previous screen.

        @return True when navigation occurred; False when history was empty.
        """
        ...

    @abstractmethod
    def go_home(self) -> None:
        """Navigate to the frontend's configured home screen."""
        ...
