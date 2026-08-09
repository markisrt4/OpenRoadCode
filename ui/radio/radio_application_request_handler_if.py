"""Requests emitted by a radio UI for its companion application."""

from abc import ABC, abstractmethod


class RadioApplicationRequestHandlerIf(ABC):
    """Handle requests affecting a companion radio application."""

    @abstractmethod
    def request_toggle_radio_application(self) -> None:
        """Request toggling the companion receiver application."""
        ...
