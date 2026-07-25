"""Interfaces and values used by navigation orientation estimators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class Orientation:
    """Represent heading, pitch, and roll in degrees."""

    heading_deg: float
    pitch_deg: float
    roll_deg: float


class OrientationEstimatorIf(ABC):
    """Convert sensor measurements into an orientation estimate."""

    @abstractmethod
    def start(self, acceleration_mps2: Vector3) -> None:
        """Initialize the estimator from the first sensor sample.

        @param acceleration_mps2 Initial x/y/z acceleration vector in m/s².
        """

    @abstractmethod
    def stop(self) -> None:
        """Release resources owned by the estimator."""

    @abstractmethod
    def update(
        self,
        acceleration_mps2: Vector3,
        angular_velocity_rad_s: Vector3,
        elapsed_s: float,
    ) -> Orientation:
        """Update the orientation estimate.

        @param acceleration_mps2 Current x/y/z acceleration vector in m/s².
        @param angular_velocity_rad_s Current x/y/z angular velocity in rad/s.
        @param elapsed_s Seconds elapsed since the previous update.
        @return Heading, pitch, and roll in degrees.
        """

    @abstractmethod
    def reset_heading(self, heading_deg: float = 0.0) -> None:
        """Set the estimator's heading reference.

        @param heading_deg New heading reference in degrees.
        """
