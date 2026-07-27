"""Public interface for navigation controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .motion_calibration import MotionCalibration
from .navigation_state import GpsState, NavigationState


class NavigationControllerIf(ABC):
    """Provide vehicle orientation, motion, and optional GPS state."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the controller is ready to read state."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether navigation support is configured and available."""

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies."""

    @property
    @abstractmethod
    def calibration(self) -> MotionCalibration | None:
        """Return the active stationary calibration, if any."""

    @abstractmethod
    def start(self) -> None:
        """Start the controller and its configured sources."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the controller and its configured sources."""

    @abstractmethod
    def reset_heading(self, heading_deg: float = 0.0) -> None:
        """Reset relative heading to the requested number of degrees."""

    @abstractmethod
    def calibrate_stationary(
        self,
        sample_count: int = 100,
        sample_interval_s: float = 0.01,
    ) -> MotionCalibration:
        """Measure motion-sensor biases while stationary."""

    @abstractmethod
    def update_gps_state(self, gps_state: GpsState) -> None:
        """Accept the latest normalized GPS report."""

    @abstractmethod
    def read_state(self) -> NavigationState:
        """Read and return the current navigation state."""
