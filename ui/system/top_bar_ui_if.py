"""Toolkit-independent UI contract for a persistent top bar."""

from abc import ABC, abstractmethod
from collections.abc import Callable


class TopBarUiIf(ABC):
    """Present screen navigation and compact vehicle status information."""

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Set the current screen or menu title.

        @param title User-visible title text.
        """
        ...

    @abstractmethod
    def set_back_action(self, action: Callable[[], None]) -> None:
        """Set the action requested by the back control.

        @param action Callback invoked by the back control.
        """
        ...

    @abstractmethod
    def show_back_button(self, text: str | None = None) -> None:
        """Show the back control, optionally with custom text.

        @param text Optional custom back-control label.
        """
        ...

    @abstractmethod
    def hide_back_button(self) -> None:
        """Hide the back control."""
        ...

    @abstractmethod
    def invoke_back_action(self) -> None:
        """Request the configured back action."""
        ...

    @abstractmethod
    def set_frequency_text(self, text: str) -> None:
        """Set the compact radio-frequency status text.

        @param text Formatted frequency text or unavailable placeholder.
        """
        ...

    @abstractmethod
    def set_location_text(self, text: str) -> None:
        """Set the compact geographic-location status text.

        @param text Formatted location text or unavailable placeholder.
        """
        ...
