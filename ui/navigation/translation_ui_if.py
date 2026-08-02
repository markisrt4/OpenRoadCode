from abc import ABC, abstractmethod

from ..ui_if import UiIf


class TranslationUiIf(UiIf, ABC):
    """Display translational motion in the vehicle coordinate frame.

    The X axis points forward, Y points left, and Z points up. Acceleration is
    linear acceleration with gravity removed. The total is the Euclidean
    magnitude of that three-axis vector. Positive climb rate is upward.
    ``None`` means a measurement is unavailable.
    """
    
    @abstractmethod
    def set_rate_of_climb(self, rate_mps: float | None) -> None:
        """
        Set the rate of climb in metres per second.
        """
        ...

    @abstractmethod
    def set_accel_x(self, acceleration_x_mps2: float | None) -> None:
        """
        Set x-axis acceleration in metres per second squared.
        """
        ...

    @abstractmethod
    def set_accel_y(self, acceleration_y_mps2: float | None) -> None:
        """
        Set y-axis acceleration in metres per second squared.
        """
        ...

    @abstractmethod
    def set_accel_z(self, acceleration_z_mps2: float | None) -> None:
        """
        Set z-axis acceleration in metres per second squared.
        """
        ...

    @abstractmethod
    def set_accel_total(self, acceleration_magnitude_mps2: float | None) -> None:
        """
        Set the total acceleration magnitude in metres per second squared.
        """
        ...   
