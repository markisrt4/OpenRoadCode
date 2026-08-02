"""UI contract for rotational motion measurements."""

from abc import ABC, abstractmethod

from ..ui_if import UiIf


class AngularVelocityUiIf(UiIf, ABC):
    """Display angular velocity about the vehicle's three axes.

    This is rotational speed, not absolute orientation. The right-handed
    vehicle frame uses X forward, Y left, and Z up. Positive values follow the
    right-hand rule. ``None`` means a measurement is unavailable.
    """

    @abstractmethod
    def set_angular_velocity_x(self, angular_velocity_x_rad_s: float | None) -> None:
        """Set angular velocity about the X axis in radians per second."""
        ...

    @abstractmethod
    def set_angular_velocity_y(self, angular_velocity_y_rad_s: float | None) -> None:
        """Set angular velocity about the Y axis in radians per second."""
        ...

    @abstractmethod
    def set_angular_velocity_z(self, angular_velocity_z_rad_s: float | None) -> None:
        """Set angular velocity about the Z axis in radians per second."""
        ...
