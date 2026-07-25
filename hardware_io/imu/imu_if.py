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
        """Return whether the IMU is initialized and available.

        @retval True The IMU is initialized and readable.
        @retval False The IMU is disconnected.
        """

    @abstractmethod
    def get_acceleration_mps2(self) -> Vector3:
        """Read acceleration.

        @return X/y/z acceleration vector in meters per second squared.
        """

    @abstractmethod
    def get_angular_velocity_rad_s(self) -> Vector3:
        """Read angular velocity.

        @return X/y/z angular-velocity vector in radians per second.
        """
