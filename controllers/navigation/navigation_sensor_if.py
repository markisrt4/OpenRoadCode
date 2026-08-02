"""Navigation-facing motion sensor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class MotionSample:
    """Represent one normalized motion-sensor sample."""

    acceleration_mps2: Vector3
    angular_velocity_rad_s: Vector3


class NavigationSensorIf(ABC):
    """Provide normalized motion samples to the navigation controller."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the motion sensor is connected and ready.

        @retval True The sensor can provide motion samples.
        @retval False The sensor is disconnected.
        """
        ...

    @abstractmethod
    def connect(self) -> None:
        """Connect to the motion sensor."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the motion sensor."""

    @abstractmethod
    def read_motion(self) -> MotionSample:
        """Read one normalized motion sample.

        @return Acceleration in m/s² and angular velocity in rad/s.
        """
