"""Interface for inertial measurement unit devices."""

from abc import ABC, abstractmethod

from hardware_io.imu.imu_types import Vector3


class ImuIf(ABC):
    """Define access to acceleration and angular velocity data."""

    @abstractmethod
    def start(self) -> None:
        """Initialize the IMU device."""

    @abstractmethod
    def stop(self) -> None:
        """Release resources associated with the IMU device."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the IMU is initialized and available."""

    @abstractmethod
    def get_acceleration_mps2(self) -> Vector3:
        """Return acceleration in meters per second squared."""

    @abstractmethod
    def get_angular_velocity_rad_s(self) -> Vector3:
        """Return angular velocity in radians per second."""
