"""Requests emitted by navigation and orientation controls."""

from abc import ABC, abstractmethod


class NavigationRequestHandlerIf(ABC):
    """Handle user requests that affect navigation estimation."""

    @abstractmethod
    def request_stationary_calibration(self) -> None:
        """Request calibration while the vehicle is stationary."""
        ...

    @abstractmethod
    def request_heading_reset(self) -> None:
        """Request that the relative heading be reset to zero."""
        ...
