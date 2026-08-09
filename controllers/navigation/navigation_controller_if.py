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
        """Return whether the controller is ready to read state.

        @retval True The controller has been started.
        @retval False The controller has not been started.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether navigation support is configured and available.

        @retval True Navigation support is available.
        @retval False Navigation support is unavailable.
        """

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies.

        @return Human-readable status, or ``None`` when no message applies.
        """

    @property
    @abstractmethod
    def calibration(self) -> MotionCalibration | None:
        """Return the active stationary calibration, if any.

        @return Active calibration, or ``None`` before calibration.
        """

    @abstractmethod
    def start(self) -> None:
        """Start the controller and its configured sources."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the controller and its configured sources."""

    @abstractmethod
    def reset_heading(self, heading_deg: float = 0.0) -> None:
        """Reset relative heading to the requested number of degrees.

        @param heading_deg Desired heading after resetting, in degrees.
        """

    @abstractmethod
    def calibrate_stationary(
        self,
        sample_count: int = 100,
        sample_interval_s: float = 0.01,
    ) -> MotionCalibration:
        """Measure motion-sensor biases while stationary.

        @param sample_count Number of stationary samples to collect.
        @param sample_interval_s Delay between samples in seconds.
        @return Measured stationary motion calibration.
        """

    @abstractmethod
    def update_gps_state(self, gps_state: GpsState) -> None:
        """Accept the latest normalized GPS report.

        @param gps_state Latest normalized GPS state.
        """

    @abstractmethod
    def read_state(self) -> NavigationState:
        """Read and return the current navigation state.

        @return Current orientation, motion, and optional GPS state.
        """
